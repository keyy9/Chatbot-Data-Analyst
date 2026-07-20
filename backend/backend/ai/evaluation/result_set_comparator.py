"""
Result-Set Comparator.

Compares two SQL query result sets (generated vs. gold) for the
SQL-correctness benchmark. This is the ground-truth signal for execution
accuracy: two queries are "correct" relative to each other if they return
the same data, regardless of superficial differences like column aliasing,
column order, or (when the gold query has no top-level ORDER BY) row
order.

Pure functions only - no database access, no LLM calls. Given two lists
of row-dicts (as already returned by `SupabaseQueryExecutor.execute()`)
and the gold SQL text (used only to detect a top-level ORDER BY), this
module decides whether they match.
"""

import logging
import math
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from itertools import permutations
from typing import Any, Dict, List, Optional

# ============ Setup Logging ============
logger = logging.getLogger(__name__)

# Above this many columns, a full permutation search over column alignment
# becomes impractical (9! = 362880) - fall back to identity alignment only.
# Benchmark queries against this schema realistically have well under 8
# columns, so this is a safety cap, not a real-world limitation.
_MAX_COLUMNS_FOR_PERMUTATION_SEARCH = 8


@dataclass
class ComparisonVerdict:
    """
    Result of comparing a generated result set against a gold one.

    Attributes:
        is_match: Whether the two result sets are considered equal.
        category: One of "correct", "value_mismatch", "row_count_mismatch".
        reason: Short human-readable explanation of the verdict.
    """
    is_match: bool
    category: str
    reason: str


def _normalize_value(value: Any, float_tolerance: float) -> Any:
    """
    Normalize a single cell value so equal-enough values compare equal.

    - None/NULL stays None.
    - bool is kept distinct from int (Python would otherwise treat
      True == 1, which is correct for arithmetic but not for a
      benchmark comparing e.g. a boolean flag column).
    - int/float/Decimal are all coerced to float and rounded to
      `float_tolerance`, so e.g. 14970759000 and 14970759000.0000001
      compare equal, and Decimal/float type differences (which don't
      compare reliably against each other in Python) stop mattering.
    - date/datetime are normalized to their ISO string form.
    - strings are stripped of surrounding whitespace.

    Args:
        value: The raw cell value.
        float_tolerance: Absolute tolerance for numeric comparison.

    Returns:
        A normalized, hashable value suitable for equality/multiset comparison.
    """
    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float, Decimal)):
        as_float = float(value)
        if float_tolerance > 0:
            ndigits = max(0, -int(math.floor(math.log10(float_tolerance))))
            as_float = round(as_float, ndigits)
        # Avoid "-0.0" != "0.0" surprises after rounding.
        return as_float + 0.0

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, str):
        return value.strip()

    return value


def _strip_strings_and_comments(sql: str) -> str:
    """
    Return a same-length "masked" version of `sql` with the contents of
    string literals and comments replaced by spaces, so a structural scan
    (paren depth, keyword search) never gets confused by an "ORDER BY"
    appearing inside a string value or a comment. Mirrors the quote-
    tracking approach already used in `sql_guard.py`'s
    `_check_multiple_statements`, extended to also blank out comments.

    Args:
        sql: The raw SQL text.

    Returns:
        str: Same length as `sql`, with string/comment contents blanked.
    """
    masked = list(sql)
    i = 0
    n = len(sql)
    in_string = False
    string_char = None

    while i < n:
        char = sql[i]

        if in_string:
            if char == string_char and sql[i - 1] != "\\":
                in_string = False
            else:
                masked[i] = " "
            i += 1
            continue

        if char in ("'", '"'):
            in_string = True
            string_char = char
            i += 1
            continue

        if char == "-" and i + 1 < n and sql[i + 1] == "-":
            while i < n and sql[i] != "\n":
                masked[i] = " "
                i += 1
            continue

        if char == "/" and i + 1 < n and sql[i + 1] == "*":
            end = sql.find("*/", i + 2)
            end = end + 2 if end != -1 else n
            for j in range(i, end):
                masked[j] = " "
            i = end
            continue

        i += 1

    return "".join(masked)


def has_top_level_order_by(sql: str) -> bool:
    """
    Detect whether `sql` has an ORDER BY clause at the top level of the
    statement (i.e. not inside a subquery, CTE body, or window function -
    those don't affect the final row order of the outer query).

    Args:
        sql: The SQL text (typically the gold SQL).

    Returns:
        bool: True if a top-level ORDER BY is present.
    """
    if not sql:
        return False

    masked = _strip_strings_and_comments(sql)

    depth = 0
    upper = masked.upper()
    idx = 0
    while idx < len(upper):
        char = upper[idx]

        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        elif depth == 0 and upper[idx:idx + 5] == "ORDER":
            # Word-boundary check, then require BY (allowing any run of
            # whitespace, matching how ORDER BY is always written).
            before_ok = idx == 0 or not (upper[idx - 1].isalnum() or upper[idx - 1] == "_")
            after = idx + 5
            if before_ok and after < len(upper):
                rest = upper[after:].lstrip(" \t\r\n")
                if rest.startswith("BY") and (len(rest) == 2 or not (rest[2].isalnum() or rest[2] == "_")):
                    return True

        idx += 1

    return False


def _row_tuple(row: Dict[str, Any], columns: List[str], float_tolerance: float) -> tuple:
    """Convert a row-dict into a normalized value tuple, ordered by `columns`."""
    return tuple(_normalize_value(row.get(col), float_tolerance) for col in columns)


def compare_result_sets(
    generated_rows: List[Dict[str, Any]],
    gold_rows: List[Dict[str, Any]],
    gold_sql: str,
    float_tolerance: float = 1e-6
) -> ComparisonVerdict:
    """
    Compare a generated query's result rows against the gold query's
    result rows.

    Column names/order may differ (aliasing is fine) - this searches for
    a column alignment (a bijection between the two sides) under which
    the rows match, either as an ORDERED sequence (if `gold_sql` has a
    top-level ORDER BY) or as an order-insensitive multiset (otherwise).
    Row-level correlation between columns is preserved throughout: rows
    are compared as whole tuples, never column-by-column independently,
    so a permutation that matches column values individually but not in
    the right combination is correctly rejected.

    Args:
        generated_rows: Rows returned by executing the generated SQL.
        gold_rows: Rows returned by executing the gold SQL.
        gold_sql: The gold SQL text (used only to detect ORDER BY).
        float_tolerance: Absolute tolerance for numeric comparison.

    Returns:
        ComparisonVerdict: The match verdict.
    """
    if len(generated_rows) != len(gold_rows):
        return ComparisonVerdict(
            is_match=False,
            category="row_count_mismatch",
            reason=f"Generated {len(generated_rows)} row(s), gold has {len(gold_rows)} row(s)"
        )

    if len(generated_rows) == 0:
        return ComparisonVerdict(is_match=True, category="correct", reason="Both result sets are empty")

    generated_columns = list(generated_rows[0].keys())
    gold_columns = list(gold_rows[0].keys())

    if len(generated_columns) != len(gold_columns):
        return ComparisonVerdict(
            is_match=False,
            category="value_mismatch",
            reason=f"Column count differs: generated {len(generated_columns)} vs gold {len(gold_columns)}"
        )

    order_sensitive = has_top_level_order_by(gold_sql)
    ncols = len(gold_columns)

    gold_row_tuples = [_row_tuple(row, gold_columns, float_tolerance) for row in gold_rows]
    gold_multiset = None if order_sensitive else Counter(gold_row_tuples)

    # Every generated row pre-computed once, in the generated column order;
    # a permutation just re-indexes into this per column-order candidate.
    generated_raw = [
        [_normalize_value(row.get(col), float_tolerance) for col in generated_columns]
        for row in generated_rows
    ]

    if ncols > _MAX_COLUMNS_FOR_PERMUTATION_SEARCH:
        candidate_perms = [tuple(range(ncols))]
        logger.warning(
            f"{ncols} columns exceeds permutation-search cap "
            f"({_MAX_COLUMNS_FOR_PERMUTATION_SEARCH}) - only checking identity column alignment"
        )
    else:
        candidate_perms = list(permutations(range(ncols)))

    for perm in candidate_perms:
        reordered = [tuple(raw[p] for p in perm) for raw in generated_raw]

        if order_sensitive:
            if reordered == gold_row_tuples:
                return ComparisonVerdict(is_match=True, category="correct", reason="Rows match in order")
        else:
            if Counter(reordered) == gold_multiset:
                return ComparisonVerdict(
                    is_match=True,
                    category="correct",
                    reason="Rows match (order-insensitive, no top-level ORDER BY in gold SQL)"
                )

    reason = (
        "No column alignment produces matching row order (gold SQL has a top-level ORDER BY, "
        "so row order matters)"
        if order_sensitive else
        "No column alignment produces a matching set of rows"
    )
    return ComparisonVerdict(is_match=False, category="value_mismatch", reason=reason)
