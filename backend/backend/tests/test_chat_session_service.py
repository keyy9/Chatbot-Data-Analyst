"""
Unit tests for chat message rendering.

`derive_chart_data` and `format_message` are pure - no database, no LLM - so
they are exercised directly on plain rows.

Why this matters: only a chart's *type* is persisted, never which column is
the axis. Those keys are re-derived on read, and the same derivation runs in
the frontend (`deriveAxisFields` in chartMapping.ts). If the two drift, a
reloaded conversation renders differently from the live one.
"""

from datetime import datetime

from backend.api.services.chat_session_service import derive_chart_data, format_message


class TestDeriveChartData:
    def test_picks_text_column_as_axis_and_numbers_as_series(self):
        rows = [{"category": "Kue Basah", "total": 42}, {"category": "Minuman", "total": 17}]

        result = derive_chart_data("bar", rows)

        assert result["type"] == "bar"
        assert result["xAxisKey"] == "category"
        assert result["dataKeys"] == ["total"]

    def test_column_is_normalised_to_bar(self):
        """The recommender may say "column"; the chart library only knows "bar"."""
        rows = [{"label": "a", "value": 1}]

        assert derive_chart_data("column", rows)["type"] == "bar"

    def test_multiple_numeric_columns_all_become_series(self):
        rows = [{"month": "Jan", "revenue": 10, "cost": 4}]

        result = derive_chart_data("line", rows)

        assert result["xAxisKey"] == "month"
        assert result["dataKeys"] == ["revenue", "cost"]

    def test_booleans_are_not_charted_as_numbers(self):
        """bool subclasses int in Python - a flag column must not become a series."""
        rows = [{"name": "a", "is_active": True, "score": 5}]

        result = derive_chart_data("bar", rows)

        assert "is_active" not in result["dataKeys"]
        assert result["dataKeys"] == ["score"]

    def test_all_numeric_falls_back_to_first_column_as_axis(self):
        rows = [{"year": 2026, "revenue": 100}]

        result = derive_chart_data("line", rows)

        assert result["xAxisKey"] == "year"
        assert result["dataKeys"] == ["revenue"]

    def test_single_numeric_column_has_no_series_left(self):
        """One numeric column becomes the axis, leaving nothing to plot."""
        assert derive_chart_data("bar", [{"total": 5}]) is None

    def test_no_numeric_column_is_not_chartable(self):
        assert derive_chart_data("bar", [{"a": "x", "b": "y"}]) is None

    def test_unsupported_chart_type_is_ignored(self):
        assert derive_chart_data("metric", [{"a": "x", "b": 1}]) is None

    def test_missing_type_or_rows_is_ignored(self):
        assert derive_chart_data(None, [{"a": "x", "b": 1}]) is None
        assert derive_chart_data("bar", []) is None
        assert derive_chart_data("bar", None) is None


def _row(**overrides):
    row = {
        "id": "msg-1",
        "role": "assistant",
        "text": "Here are the results.",
        "sql": "SELECT 1",
        "result_json": None,
        "chart_type": None,
        "needs_clarification": False,
        "timestamp": datetime(2026, 7, 27, 10, 30),
    }
    row.update(overrides)
    return row


class TestFormatMessage:
    def test_assistant_role_maps_to_ai_sender(self):
        assert format_message(_row())["sender"] == "ai"

    def test_user_role_maps_to_user_sender(self):
        assert format_message(_row(role="user", sql=None))["sender"] == "user"

    def test_timestamp_becomes_epoch_milliseconds(self):
        result = format_message(_row())

        assert result["timestamp"] == int(datetime(2026, 7, 27, 10, 30).timestamp() * 1000)

    def test_result_json_string_is_decoded_into_a_preview(self):
        result = format_message(_row(result_json='[{"a": 1, "b": 2}]'))

        assert result["resultPreview"] == {"columns": ["a", "b"], "rows": [{"a": 1, "b": 2}]}

    def test_malformed_result_json_does_not_break_the_message(self):
        result = format_message(_row(result_json="{not json"))

        assert result["resultPreview"] is None
        assert result["text"] == "Here are the results."

    def test_clarification_carries_its_options_instead_of_a_preview(self):
        result = format_message(_row(needs_clarification=True, result_json='["by month", "by year"]'))

        assert result["isClarification"] is True
        assert result["clarificationOptions"] == ["by month", "by year"]

    def test_non_clarification_has_no_options(self):
        assert format_message(_row())["clarificationOptions"] is None

    def test_assistant_error_without_sql_is_marked_failed(self):
        result = format_message(_row(sql=None, text="Database error: relation does not exist"))

        assert result["status"] == "Failed"

    def test_assistant_answer_with_sql_stays_successful(self):
        assert format_message(_row())["status"] == "Success"

    def test_user_message_mentioning_error_is_not_marked_failed(self):
        """Only the assistant's own failures count - a user may ask about errors."""
        result = format_message(_row(role="user", sql=None, text="why do I get an error?"))

        assert result["status"] == "Success"

    def test_chart_data_is_rebuilt_when_a_type_was_stored(self):
        result = format_message(_row(
            chart_type="bar",
            result_json=[{"category": "Kue Basah", "total": 42}],
        ))

        assert result["chartData"]["xAxisKey"] == "category"
        assert result["chartData"]["dataKeys"] == ["total"]
