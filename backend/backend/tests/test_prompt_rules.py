"""
Unit tests for the two prompt rules that were producing wrong answers.

Both are pure functions - no database, no LLM.

Background: the explainer never saw the SQL, so a `LIMIT 1` result read to it
like "the table contains one row", and it told users things like "Home is the
only category we have data for". And the ambiguity bypass listed
"highest"/"lowest" but not "most", so "Which city has the most customers?" fell
through to the LLM check and came back as a clarification request instead of an
answer.
"""

import re

from backend.ai.prompts.clarification_prompt import RANKING_PHRASE_PATTERN
from backend.ai.prompts.explanation_prompt import describe_query_scope


def is_self_specifying(question: str) -> bool:
    """Mirror of the bypass check in detect_ambiguity."""
    return bool(re.search(RANKING_PHRASE_PATTERN, question.lower()))


class TestRankingPhraseBypass:
    def test_superlative_questions_are_not_ambiguous(self):
        for question in [
            "Which city has the most customers?",
            "What is the most popular payment method among paid payments?",
            "Which product has the least stock?",
            "Which category has the fewest products?",
            "What is the largest order total?",
            "Which product is the cheapest?",
            "What are the best-selling products?",
        ]:
            assert is_self_specifying(question), question

    def test_per_group_questions_are_not_ambiguous(self):
        assert is_self_specifying("How many customers are in each tier?")
        assert is_self_specifying("Revenue per category")

    def test_numbered_top_n_is_not_ambiguous(self):
        assert is_self_specifying("Show the top 5 products")
        assert is_self_specifying("Give me the bottom 3 cities")

    def test_almost_is_not_read_as_most(self):
        """Word-boundary matching - otherwise "almost" would bypass the check."""
        assert not is_self_specifying("almost done")

    def test_genuinely_vague_questions_still_go_through_the_check(self):
        assert not is_self_specifying("Show me the customer")
        assert not is_self_specifying("What about sales?")


class TestDescribeQueryScope:
    def test_limit_is_flagged_so_top_n_is_not_read_as_everything(self):
        scope = describe_query_scope(
            "SELECT category, COUNT(*) FROM products GROUP BY category "
            "ORDER BY 2 DESC LIMIT 1",
            row_count=1,
        )

        assert "TOP 1" in scope
        assert "More rows exist" in scope
        assert "Never say this is all the data" in scope

    def test_group_by_rows_are_described_as_groups(self):
        scope = describe_query_scope(
            "SELECT tier, COUNT(*) FROM customers GROUP BY tier ORDER BY tier",
            row_count=3,
        )

        assert "one group" in scope

    def test_single_aggregate_is_described_as_one_overall_figure(self):
        scope = describe_query_scope(
            "SELECT ROUND(AVG(unit_price), 2) FROM products", row_count=1
        )

        assert "one overall figure" in scope

    def test_where_filter_is_surfaced(self):
        scope = describe_query_scope(
            "SELECT SUM(amount) FROM payments WHERE status = 'paid'", row_count=1
        )

        assert "status = 'paid'" in scope

    def test_where_is_not_confused_by_trailing_clauses(self):
        scope = describe_query_scope(
            "SELECT city, COUNT(*) FROM customers WHERE tier = 'Gold' "
            "GROUP BY city ORDER BY 2 DESC LIMIT 3",
            row_count=3,
        )

        assert "tier = 'Gold'" in scope
        assert "GROUP BY" not in scope.split("filter are included:")[1]

    def test_empty_result_is_called_out(self):
        scope = describe_query_scope("SELECT * FROM orders WHERE status = 'x'", row_count=0)

        assert "No records matched" in scope

    def test_plain_query_says_the_result_is_complete(self):
        scope = describe_query_scope("SELECT product_name FROM products", row_count=201)

        assert "complete result" in scope

    def test_missing_sql_does_not_crash(self):
        assert describe_query_scope(None, row_count=0)
        assert describe_query_scope("", row_count=5)

    def test_lowercase_sql_is_handled(self):
        scope = describe_query_scope("select city from customers limit 5", row_count=5)

        assert "TOP 5" in scope
