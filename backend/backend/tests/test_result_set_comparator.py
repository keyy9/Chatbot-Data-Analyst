"""
Unit tests for `result_set_comparator.py`.

Pure-function tests, no database/LLM dependency - covers the comparator's
core contract: value normalization (float tolerance, NULL), row/column
alignment (aliasing, reordering), order sensitivity driven by whether the
gold SQL has a top-level ORDER BY, and correlated-value correctness
(swapped pairings must fail even when each column's values individually
"look" present on both sides).
"""

from backend.ai.evaluation.result_set_comparator import (
    compare_result_sets,
    has_top_level_order_by,
)


class TestCompareResultSets:
    """Tests for `compare_result_sets`."""

    def test_identical_results(self):
        result = compare_result_sets(
            generated_rows=[{"a": 1, "b": 2}],
            gold_rows=[{"a": 1, "b": 2}],
            gold_sql="SELECT a, b FROM t"
        )
        assert result.is_match is True
        assert result.category == "correct"

    def test_reordered_columns(self):
        """Column names/order may differ (aliasing) - still correct."""
        result = compare_result_sets(
            generated_rows=[{"x": 2, "y": 1}],
            gold_rows=[{"y": 1, "x": 2}],
            gold_sql="SELECT y, x FROM t"
        )
        assert result.is_match is True
        assert result.category == "correct"

    def test_reordered_rows_without_order_by_passes(self):
        """No top-level ORDER BY in gold SQL -> row order must not matter."""
        generated = [{"name": "B", "v": 2}, {"name": "A", "v": 1}]
        gold = [{"name": "A", "v": 1}, {"name": "B", "v": 2}]

        result = compare_result_sets(generated, gold, "SELECT name, v FROM t")

        assert result.is_match is True
        assert result.category == "correct"

    def test_reordered_rows_with_gold_order_by_fails(self):
        """Gold SQL has a top-level ORDER BY -> row order matters, must fail."""
        generated = [{"name": "B", "v": 2}, {"name": "A", "v": 1}]
        gold = [{"name": "A", "v": 1}, {"name": "B", "v": 2}]

        result = compare_result_sets(generated, gold, "SELECT name, v FROM t ORDER BY name")

        assert result.is_match is False
        assert result.category == "value_mismatch"

    def test_float_tolerance_within_bound_passes(self):
        result = compare_result_sets(
            generated_rows=[{"avg": 1.0000001}],
            gold_rows=[{"avg": 1.0000002}],
            gold_sql="SELECT avg FROM t",
            float_tolerance=1e-6
        )
        assert result.is_match is True

    def test_float_tolerance_outside_bound_fails(self):
        result = compare_result_sets(
            generated_rows=[{"avg": 1.1}],
            gold_rows=[{"avg": 1.2}],
            gold_sql="SELECT avg FROM t",
            float_tolerance=1e-6
        )
        assert result.is_match is False
        assert result.category == "value_mismatch"

    def test_null_handling(self):
        result = compare_result_sets(
            generated_rows=[{"a": None, "b": 1}],
            gold_rows=[{"a": None, "b": 1}],
            gold_sql="SELECT a, b FROM t"
        )
        assert result.is_match is True

    def test_null_vs_value_mismatch(self):
        result = compare_result_sets(
            generated_rows=[{"a": None}],
            gold_rows=[{"a": 0}],
            gold_sql="SELECT a FROM t"
        )
        assert result.is_match is False

    def test_extra_row_is_row_count_mismatch(self):
        result = compare_result_sets(
            generated_rows=[{"a": 1}, {"a": 2}],
            gold_rows=[{"a": 1}],
            gold_sql="SELECT a FROM t"
        )
        assert result.is_match is False
        assert result.category == "row_count_mismatch"

    def test_missing_row_is_row_count_mismatch(self):
        result = compare_result_sets(
            generated_rows=[{"a": 1}],
            gold_rows=[{"a": 1}, {"a": 2}],
            gold_sql="SELECT a FROM t"
        )
        assert result.is_match is False
        assert result.category == "row_count_mismatch"

    def test_swapped_value_columns_fail(self):
        """
        Row-level correlation must be preserved: each column's values are
        individually present on both sides, but paired with the wrong
        row - this must NOT be reported as a match.
        """
        generated = [{"name": "A", "v": 2}, {"name": "B", "v": 1}]  # swapped v's
        gold = [{"name": "A", "v": 1}, {"name": "B", "v": 2}]

        result = compare_result_sets(generated, gold, "SELECT name, v FROM t")

        assert result.is_match is False
        assert result.category == "value_mismatch"

    def test_both_empty_is_correct(self):
        result = compare_result_sets([], [], "SELECT a FROM t")
        assert result.is_match is True
        assert result.category == "correct"

    def test_column_count_mismatch(self):
        result = compare_result_sets(
            generated_rows=[{"a": 1, "b": 2}],
            gold_rows=[{"a": 1}],
            gold_sql="SELECT a FROM t"
        )
        assert result.is_match is False
        assert result.category == "value_mismatch"

    def test_string_whitespace_is_stripped(self):
        result = compare_result_sets(
            generated_rows=[{"name": "  Alice  "}],
            gold_rows=[{"name": "Alice"}],
            gold_sql="SELECT name FROM t"
        )
        assert result.is_match is True

    def test_decimal_and_float_compare_equal(self):
        from decimal import Decimal
        result = compare_result_sets(
            generated_rows=[{"total": Decimal("120000.00")}],
            gold_rows=[{"total": 120000}],
            gold_sql="SELECT total FROM t"
        )
        assert result.is_match is True


class TestHasTopLevelOrderBy:
    """Tests for `has_top_level_order_by`."""

    def test_top_level_order_by_detected(self):
        assert has_top_level_order_by("SELECT x FROM t ORDER BY x") is True

    def test_no_order_by(self):
        assert has_top_level_order_by("SELECT x FROM t WHERE x > 1") is False

    def test_order_by_inside_subquery_ignored(self):
        sql = "SELECT * FROM (SELECT x FROM t ORDER BY x) sub"
        assert has_top_level_order_by(sql) is False

    def test_order_by_inside_subquery_but_also_at_top_level(self):
        sql = "SELECT x FROM (SELECT x FROM t ORDER BY x) sub ORDER BY x"
        assert has_top_level_order_by(sql) is True

    def test_order_by_inside_string_literal_ignored(self):
        sql = "SELECT x FROM t WHERE name = 'order by fake'"
        assert has_top_level_order_by(sql) is False

    def test_order_by_inside_comment_ignored(self):
        sql = "SELECT x FROM t -- ORDER BY should not count here\nWHERE x > 1"
        assert has_top_level_order_by(sql) is False

    def test_empty_sql(self):
        assert has_top_level_order_by("") is False

    def test_none_sql(self):
        assert has_top_level_order_by(None) is False
