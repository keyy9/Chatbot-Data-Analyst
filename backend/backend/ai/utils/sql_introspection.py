"""
SQL Introspection Utilities.

Small regex-based helpers for pulling table/column references out of a
SQL string. Used by RBAC (which tables is this touching), evaluation
(hallucination/schema-compliance checks), and source attribution
(which tables/columns did this answer actually come from).

This is intentionally lightweight (regex, not a real SQL parser) since
it only needs to work on SQL that already passed SQLGuardValidator.
"""

import re
from typing import Dict, List

# Matches the table name following FROM / JOIN / INTO / UPDATE (with optional
# schema-qualification and any JOIN variant).
_TABLE_PATTERN = re.compile(
    r'\b(?:FROM|JOIN|INTO|UPDATE)\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?)',
    re.IGNORECASE
)

# Matches table.column references (e.g. "o.order_id" or "orders.amount").
_TABLE_COLUMN_PATTERN = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)\b')


def extract_tables(sql: str) -> List[str]:
    """
    Extract table names referenced in a SQL query.

    Args:
        sql: The SQL query.

    Returns:
        List[str]: Unique table names (schema-qualifier stripped), in
            first-seen order.
    """
    seen = []
    for match in _TABLE_PATTERN.findall(sql):
        table = match.split(".")[-1].lower()
        if table not in seen:
            seen.append(table)
    return seen


def extract_columns(sql: str) -> Dict[str, List[str]]:
    """
    Extract table.column references from a SQL query.

    Only finds columns that are explicitly qualified with a table/alias
    prefix (e.g. "o.amount"); bare column names in an unqualified SELECT
    are not attributable to a specific table via regex alone.

    Args:
        sql: The SQL query.

    Returns:
        Dict[str, List[str]]: Mapping of table/alias -> unique column names.
    """
    columns: Dict[str, List[str]] = {}

    for table, col in _TABLE_COLUMN_PATTERN.findall(sql):
        table_key = table.lower()
        col_lower = col.lower()
        columns.setdefault(table_key, [])
        if col_lower not in columns[table_key]:
            columns[table_key].append(col_lower)

    return columns
