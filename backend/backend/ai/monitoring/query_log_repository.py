"""
Query Log Repository.

Persists every NL question + generated SQL + outcome to the `query_logs`
table - the project's "query log / show-the-SQL transparency view"
deliverable. Logging is best-effort: a logging failure (e.g. an invalid
or unknown user/session id) must never break the user-facing answer, so
failures here are caught and logged as a warning rather than raised.
"""

import logging
from typing import Optional

from backend.ai.utils.supabase_client import SupabaseClient

logger = logging.getLogger(__name__)


def log_query(
    client: SupabaseClient,
    user_id: Optional[str],
    session_id: Optional[str],
    nl_query: str,
    sql_generated: Optional[str],
    status: str,
    reject_reason: Optional[str] = None,
    exec_time_ms: Optional[float] = None
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
    """
    try:
        client.execute_write(
            """
            INSERT INTO query_logs
                (user_id, session_id, nl_query, sql_generated, status, reject_reason, exec_time_ms)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                user_id,
                session_id,
                nl_query,
                sql_generated,
                status,
                reject_reason,
                int(exec_time_ms) if exec_time_ms is not None else None
            )
        )
    except Exception as e:
        logger.warning(f"Failed to write query_logs entry (non-fatal): {str(e)}")
