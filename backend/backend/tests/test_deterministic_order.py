"""
Unit tests for `ensure_deterministic_order`.

Pure function - no database, no LLM.

Background: a `GROUP BY` with no `ORDER BY` returns rows in whatever order
Postgres finds convenient, so "how many customers are in each tier" could come
back in a different order each run. The benchmark's gold queries order their
output, so those runs scored as mismatches even though the numbers were right.
The prompt asks for an explicit ORDER BY; this guarantees one.
"""

from backend.ai.llm.generator import ensure_deterministic_order


class TestAddsOrdering:
    def test_grouped_query_without_ordering_gets_it(self):
        result = ensure_deterministic_order(
            "SELECT tier, COUNT(*) AS customer_count FROM customers GROUP BY tier"
        )

        assert result.endswith("ORDER BY 1")

    def test_trailing_semicolon_is_handled(self):
        result = ensure_deterministic_order(
            "SELECT city, COUNT(*) FROM customers GROUP BY city;"
        )

        assert result == "SELECT city, COUNT(*) FROM customers GROUP BY city ORDER BY 1"

    def test_lowercase_sql_is_recognised(self):
        result = ensure_deterministic_order(
            "select tier, count(*) from customers group by tier"
        )

        assert result.endswith("ORDER BY 1")

    def test_grouped_query_with_where_still_gets_ordering(self):
        result = ensure_deterministic_order(
            "SELECT city, COUNT(*) FROM customers WHERE tier = 'Gold' GROUP BY city"
        )

        assert result.endswith("ORDER BY 1")


class TestLeavesQueryAlone:
    def test_existing_ordering_is_respected(self):
        sql = "SELECT tier, COUNT(*) FROM customers GROUP BY tier ORDER BY COUNT(*) DESC"

        assert ensure_deterministic_order(sql) == sql

    def test_ranking_with_limit_is_untouched(self):
        """A LIMIT without ORDER BY is a deliberate ranking - reordering it
        could change which rows come back, not just their order."""
        sql = "SELECT category, COUNT(*) FROM products GROUP BY category LIMIT 5"

        assert ensure_deterministic_order(sql) == sql

    def test_query_without_group_by_is_untouched(self):
        sql = "SELECT product_name FROM products WHERE unit_price > 100"

        assert ensure_deterministic_order(sql) == sql

    def test_plain_aggregate_is_untouched(self):
        sql = "SELECT ROUND(AVG(unit_price), 2) FROM products"

        assert ensure_deterministic_order(sql) == sql

    def test_empty_input_does_not_crash(self):
        assert ensure_deterministic_order("") == ""
        assert ensure_deterministic_order(None) is None

    def test_ordering_is_added_once_only(self):
        """Running it twice must not stack a second ORDER BY."""
        once = ensure_deterministic_order(
            "SELECT tier, COUNT(*) FROM customers GROUP BY tier"
        )
        twice = ensure_deterministic_order(once)

        assert once == twice
        assert twice.count("ORDER BY") == 1
