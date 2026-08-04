"""
Unit tests for write-intent detection.

Pure function - no database, no LLM.

This guard runs before any SQL is generated for a read-only caller, so it is
the only thing standing between "delete all cancelled orders" and the model
quietly reinterpreting it as a SELECT. It has to catch real write requests
without swallowing ordinary questions that merely mention a write verb.
"""

from backend.ai.validators.write_intent import has_write_intent


class TestDetectsWrites:
    def test_leading_write_verbs_are_caught(self):
        for question in [
            "Delete all cancelled orders",
            "Update the price of product 1 to 0",
            "Insert a new customer named Test",
            "Drop the orders table",
            "Truncate payments",
            "Create a new table",
            "Alter the customers table",
        ]:
            assert has_write_intent(question), question

    def test_detection_is_case_insensitive(self):
        assert has_write_intent("DELETE ALL ORDERS")
        assert has_write_intent("Delete all orders")

    def test_leading_whitespace_does_not_hide_the_verb(self):
        assert has_write_intent("   delete everything")

    def test_change_phrasing_with_a_target_is_caught(self):
        assert has_write_intent("Change the status to completed")
        assert has_write_intent("Modify the price from 100")


class TestLeavesReadsAlone:
    def test_ordinary_questions_pass(self):
        for question in [
            "How many customers are there in total?",
            "Which city has the most customers?",
            "What is the average product price?",
            "Show the top 5 products by revenue",
        ]:
            assert not has_write_intent(question), question

    def test_a_write_verb_mid_sentence_is_not_a_write_request(self):
        """"...had a status update" is a question about data, not a command."""
        assert not has_write_intent("How many orders had a status update?")
        assert not has_write_intent("When was the last insert recorded?")

    def test_change_without_a_target_is_not_a_write(self):
        assert not has_write_intent("Change the report")

    def test_empty_and_none_are_safe(self):
        assert not has_write_intent("")
        assert not has_write_intent(None)
