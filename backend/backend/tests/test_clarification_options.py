"""
Unit tests for the clarifying questions asked about vague requests.

Only `generate_clarification_question` is exercised here, and it is pure - no
database, no LLM. Detection is deliberately NOT called: `detect_ambiguity`
reaches an LLM for anything the keyword bypass doesn't catch, which made an
earlier version of this file take minutes and fail whenever the provider was
rate-limited. Whether a question *is* vague is a model judgement covered by the
routing evaluation; what the user is *asked back* is a rule, and belongs here.

Regression cover: options used to be fragments ("All items", "Show me
available options", "Most recent"). Picking one sends that text back as the
next question, so a fragment arrived on its own and was answered as if it were
the whole request - real rows like `All items` and `Show me available options`
ended up in query_logs as if a user had asked them. Every option must now stand
on its own as a question.
"""

from backend.ai.prompts.clarification_prompt import (
    AmbiguityType,
    get_clarification_prompt_manager,
)

manager = get_clarification_prompt_manager()

# The vague questions we have actually seen, paired with the ambiguity the
# detector reports for each (confirmed against the running pipeline).
VAGUE_CASES = [
    ("Show me the customer", AmbiguityType.ENTITY_SELECTION),
    ("Compare sales", AmbiguityType.TIME_PERIOD),
    ("How did we do recently?", AmbiguityType.DATE_RANGE),
    ("Show the price", AmbiguityType.COLUMN_AMBIGUITY),
    ("What about products?", AmbiguityType.ENTITY_SELECTION),
]

VAGUE = [question for question, _ in VAGUE_CASES]

# Fragments that cannot be answered on their own.
FRAGMENTS = {
    "all items", "show me available options", "most recent",
    "highest value", "primary metric", "all metrics", "let me rephrase",
    "custom date range",
}


_AMBIGUITY_OF = dict(VAGUE_CASES)


def _options_for(question):
    """Build the clarification for a question without invoking detection."""
    clarification = manager.generate_clarification_question(
        _AMBIGUITY_OF[question], question
    )
    return clarification.question, clarification.options


class TestOptionsAreSelfContained:
    def test_no_option_is_a_bare_fragment(self):
        for question in VAGUE:
            _, options = _options_for(question)
            for option in options:
                assert option.strip().lower() not in FRAGMENTS, f"{question} -> {option}"

    def test_every_option_is_a_full_phrase(self):
        """A usable option carries a verb or a question word, not one noun."""
        for question in VAGUE:
            _, options = _options_for(question)
            for option in options:
                assert len(option.split()) >= 3, f"{question} -> {option!r} is too short"

    def test_options_are_offered_and_distinct(self):
        for question in VAGUE:
            _, options = _options_for(question)
            assert len(options) >= 3, question
            assert len(set(options)) == len(options), f"duplicate options for {question}"


class TestQuestionRefersToWhatWasAsked:
    def test_entity_question_names_the_subject(self):
        asked, _ = _options_for("Show me the customer")

        assert "customer" in asked.lower()
        assert "item" not in asked.lower(), "the old wording said 'which specific item'"

    def test_options_name_the_subject_too(self):
        _, options = _options_for("What about products?")

        assert all("product" in o.lower() for o in options)

    def test_period_question_quotes_the_original(self):
        asked, options = _options_for("Compare sales")

        assert "compare sales" in asked.lower()
        assert all("compare sales" in o.lower() for o in options)


class TestSubjectDetection:
    def test_known_subjects_are_recognised(self):
        for question, expected in [
            ("Show me the customer", "customers"),
            ("What about products?", "products"),
            ("Tell me about the order", "orders"),
            ("Which payment though?", "payments"),
        ]:
            clarification = manager.generate_clarification_question(
                AmbiguityType.ENTITY_SELECTION, question
            )
            assert any(expected in o.lower() for o in clarification.options), question

    def test_unknown_subject_falls_back_without_crashing(self):
        clarification = manager.generate_clarification_question(
            AmbiguityType.ENTITY_SELECTION, "show me the thingamajig"
        )

        assert clarification.options
        assert all(len(o.split()) >= 3 for o in clarification.options)

    def test_empty_question_is_handled(self):
        clarification = manager.generate_clarification_question(
            AmbiguityType.ENTITY_SELECTION, ""
        )

        assert clarification.question
        assert clarification.options


class TestPluralisation:
    def test_regular_and_irregular_endings(self):
        plural = manager._pluralize
        assert plural("customer") == "customers"
        assert plural("category") == "categories"
        assert plural("city") == "cities"
        assert plural("match") == "matches"
