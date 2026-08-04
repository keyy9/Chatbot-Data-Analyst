"""
Query Log Repository.

Persists every NL question + generated SQL + outcome to the `query_logs`
table - the project's "query log / show-the-SQL transparency view"
deliverable. Logging is best-effort: a logging failure (e.g. an invalid
or unknown user/session id) must never break the user-facing answer, so
failures here are caught and logged as a warning rather than raised.
"""

import logging
from typing import Any, Dict, List, Optional

from backend.ai.utils.supabase_client import SupabaseClient
from backend.ai.utils.timestamps import to_utc_iso

logger = logging.getLogger(__name__)


USAGE_COLUMNS = (
    "model_provider", "model_name", "input_tokens",
    "output_tokens", "estimated_cost", "llm_latency_ms",
)

# Probed once per process rather than per write - the answer only changes when
# a migration is applied, which needs a restart to take effect anyway.
_usage_columns_present: Optional[bool] = None


def reset_usage_column_cache() -> None:
    """Forget the probed result. For tests, and after applying a migration."""
    global _usage_columns_present
    _usage_columns_present = None


def has_usage_columns(client: SupabaseClient) -> bool:
    """
    Whether `query_logs` carries the LLM-usage columns yet.

    Checked instead of assumed because the usage migration is applied
    separately. Writing an INSERT that names columns which do not exist fails
    the whole statement - and since logging is best-effort, that failure is
    swallowed and the row is lost. Probing first keeps the log filling either
    way, with usage figures once the migration lands.

    On any probe error this reports False: writing a row without usage beats
    writing no row at all.
    """
    global _usage_columns_present

    if _usage_columns_present is None:
        try:
            rows, _, _ = client.execute_read(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'query_logs' AND column_name = ANY(%s)",
                (list(USAGE_COLUMNS),)
            )
            _usage_columns_present = len(rows) == len(USAGE_COLUMNS)

            if not _usage_columns_present:
                logger.warning(
                    "query_logs has no LLM-usage columns - logging questions "
                    "without token/cost figures. Apply "
                    "migrations/20260727_add_llm_usage_to_query_logs.sql to capture them."
                )
        except Exception as e:
            logger.warning(f"Could not probe query_logs columns, assuming none: {e}")
            _usage_columns_present = False

    return _usage_columns_present


def _to_api_shape(row: Dict[str, Any]) -> Dict[str, Any]:
    """Render one `query_logs` row into the shape the log views consume."""
    return {
        "id": str(row["id"]),
        "question": row["nl_query"],
        "generatedSql": row["sql_generated"] or "",
        "executionTimeMs": row["exec_time_ms"] or 0,
        "status": "Success" if row["status"] == "success" else "Failed",
        "timestamp": to_utc_iso(row["created_at"]),
        "errorDetail": row["reject_reason"],
    }


def list_for_user(client: SupabaseClient, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Return one user's own query history, newest first.

    Self-scoped by construction: `user_id` says whose history to read, not a
    filter the caller can widen, so this cannot surface another user's rows.
    """
    rows, _, _ = client.execute_read(
        """
        SELECT id, nl_query, sql_generated, status, reject_reason, exec_time_ms, created_at
        FROM query_logs
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT %s
        """,
        (user_id, limit)
    )
    return [_to_api_shape(row) for row in rows]


def log_query(
    client: SupabaseClient,
    user_id: Optional[str],
    session_id: Optional[str],
    nl_query: str,
    sql_generated: Optional[str],
    status: str,
    reject_reason: Optional[str] = None,
    exec_time_ms: Optional[float] = None,
    model_provider: Optional[str] = None,
    llm_usage: Optional[dict] = None
) -> None:
    """
    Insert one row into `query_logs`.

    Args:
        client: SupabaseClient instance.
        user_id: The requesting user's id (UUID string), if known.
        session_id: The chat session id (UUID string), if known.
        nl_query: The user's natural language question.
        sql_generated: The SQL that was generated (if any).
        status: One of "success", "clarification_needed", "rejected", "error".
        reject_reason: Why the query was rejected/errored, if applicable.
        exec_time_ms: Query execution time in milliseconds, if executed.
        model_provider: Which LLM provider answered ("groq"/"gemini"), if any.
        llm_usage: Token/cost/latency totals for this question, as produced by
            `backend.ai.llm.generator.aggregate_llm_usage`. Left as None for
            paths that never call an LLM (raw table browsing, direct SQL).

    Note:
        The usage columns come from `migrations/20260727_add_llm_usage_to_query_logs.sql`.
        When that migration has not been applied, the row is still written -
        just without the usage figures. Logging must never depend on a pending
        migration: silently writing nothing would empty the Query Logs view.
    """
    usage = llm_usage or {}

    base_columns = (
        user_id,
        session_id,
        nl_query,
        sql_generated,
        status,
        reject_reason,
        int(exec_time_ms) if exec_time_ms is not None else None,
    )

    try:
        if has_usage_columns(client):
            client.execute_write(
                """
                INSERT INTO query_logs
                    (user_id, session_id, nl_query, sql_generated, status, reject_reason, exec_time_ms,
                     model_provider, model_name, input_tokens, output_tokens, estimated_cost, llm_latency_ms)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    *base_columns,
                    model_provider,
                    usage.get("model_name"),
                    usage.get("input_tokens"),
                    usage.get("output_tokens"),
                    usage.get("estimated_cost"),
                    int(usage["llm_latency_ms"]) if usage.get("llm_latency_ms") is not None else None,
                )
            )
        else:
            client.execute_write(
                """
                INSERT INTO query_logs
                    (user_id, session_id, nl_query, sql_generated, status, reject_reason, exec_time_ms)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                base_columns
            )
    except Exception as e:
        logger.warning(f"Failed to write query_logs entry (non-fatal): {str(e)}")
