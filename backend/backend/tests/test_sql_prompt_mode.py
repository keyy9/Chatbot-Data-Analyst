"""
Unit tests for the read-only vs write closing instruction.

Pure functions - no database, no LLM.

Regression cover: the user prompt ended with "Return only the PostgreSQL SELECT
query" for EVERY request, including admin writes whose system prompt says the
opposite. The closing line is the last thing the model reads and it won, so
"delete the customer named X" came back as a SELECT - no error, no confirmation
step, and nothing deleted. An admin had no way to tell the write had not
happened.
"""

from backend.ai.prompts.sql_prompt import get_sql_prompt_manager

manager = get_sql_prompt_manager()


class TestReadOnlyMode:
    def test_closing_line_asks_for_a_select(self):
        prompt = manager.build_user_prompt("Show all products")

        assert prompt.rstrip().endswith("Return only the PostgreSQL SELECT query.")

    def test_read_only_is_the_default(self):
        explicit = manager.build_user_prompt("Show all products", allow_writes=False)
        default = manager.build_user_prompt("Show all products")

        assert explicit == default


class TestWriteMode:
    def test_closing_line_no_longer_demands_a_select(self):
        prompt = manager.build_user_prompt("Delete all cancelled orders", allow_writes=True)

        assert "Return only the PostgreSQL SELECT query." not in prompt

    def test_closing_line_names_the_write_statements(self):
        prompt = manager.build_user_prompt("Delete all cancelled orders", allow_writes=True)

        for statement in ("INSERT", "UPDATE", "DELETE"):
            assert statement in prompt

    def test_closing_line_forbids_a_select_for_modifications(self):
        prompt = manager.build_user_prompt("Delete all cancelled orders", allow_writes=True)

        assert "never a SELECT" in prompt


class TestQuestionSurvives:
    def test_the_request_is_present_in_both_modes(self):
        question = "Delete the customer named Customer 856"

        assert question in manager.build_user_prompt(question)
        assert question in manager.build_user_prompt(question, allow_writes=True)

    def test_conversation_context_is_included(self):
        prompt = manager.build_user_prompt(
            "and the next one?", conversation_context="RECENT: asked about orders"
        )

        assert "RECENT: asked about orders" in prompt


class TestCompletePrompt:
    def test_write_mode_reaches_the_assembled_prompt(self):
        built = manager.build_complete_prompt(
            user_question="Delete all cancelled orders",
            schema_definition="Table: orders",
            override_system_prompt="ADMIN PROMPT",
            allow_writes=True,
        )

        assert "never a SELECT" in built["user"]
        assert built["system"].startswith("ADMIN PROMPT")

    def test_read_mode_reaches_the_assembled_prompt(self):
        built = manager.build_complete_prompt(
            user_question="Show all products",
            schema_definition="Table: products",
        )

        assert built["user"].rstrip().endswith("Return only the PostgreSQL SELECT query.")

    def test_schema_is_injected_in_both_modes(self):
        for allow in (False, True):
            built = manager.build_complete_prompt(
                user_question="anything",
                schema_definition="Table: products (~ 201 rows)",
                allow_writes=allow,
            )
            assert "Table: products" in built["system"]
