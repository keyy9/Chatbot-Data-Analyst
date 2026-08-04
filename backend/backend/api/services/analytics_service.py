"""
Admin analytics service.

Aggregates the persisted `query_logs` table for the admin dashboard: the
all-users log feed, success/error rates, daily volume, per-provider token and
cost totals, and re-running one logged SELECT so its output can be inspected.
"""

import logging
from typing import Any, Dict, List

from backend.ai.utils.supabase_client import get_app_db_client
from backend.ai.utils.supabase_executor import get_supabase_query_executor
from backend.ai.utils.timestamps import to_utc_iso
from backend.api.services.errors import ServiceError

logger = logging.getLogger(__name__)

MAX_VOLUME_DAYS = 90
MAX_INSPECT_ROWS = 100


def log_admin_write(admin_id: str, executed_sql: str, affected_rows: int) -> None:
    """
    Record a confirmed admin write in `admin_action_logs`.

    Best-effort: the write already succeeded by this point, so failing to
    record it must not turn a completed operation into an error response.
    """
    try:
        get_app_db_client().execute_write(
            """
            INSERT INTO admin_action_logs (admin_id, action_type, sql_executed, affected_rows)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (admin_id, "confirmed_write", executed_sql, str(affected_rows))
        )
    except Exception as e:
        logger.warning(f"Failed to record admin action log (non-fatal): {e}")


def _author_name(row: Dict[str, Any]) -> str:
    """
    Name to show for a log's author, resolved from `users`.

    Older accounts predate the username column, so fall back to the email's
    local part - the same rule the user-management list uses.
    """
    if row["user_username"]:
        return row["user_username"]
    if row["user_email"]:
        return row["user_email"].split("@")[0]
    return "Unknown user"


def list_all_query_logs(limit: int = 100) -> List[Dict[str, Any]]:
    """Return the newest query log entries across every user."""
    client = get_app_db_client()

    rows, _, _ = client.execute_read(
        """
        SELECT ql.id, ql.nl_query, ql.sql_generated, ql.status, ql.reject_reason,
               ql.exec_time_ms, ql.created_at,
               u.id AS user_id, u.email AS user_email, u.username AS user_username,
               u.deleted_at AS user_deleted_at
        FROM query_logs ql
        LEFT JOIN users u ON u.id = ql.user_id
        ORDER BY ql.created_at DESC
        LIMIT %s
        """,
        (limit,)
    )

    return [
        {
            "id": str(row["id"]),
            "user": _author_name(row),
            "userEmail": row["user_email"],
            # The account is gone (hard-deleted, so the LEFT JOIN found no
            # row) or soft-deleted. Sent as a flag so the UI never has to
            # guess by string-matching names against the managed-user list.
            "userDeleted": row["user_id"] is None or row["user_deleted_at"] is not None,
            "question": row["nl_query"],
            "generatedSql": row["sql_generated"] or "",
            "executionTimeMs": row["exec_time_ms"] or 0,
            "status": "Success" if row["status"] == "success" else "Failed",
            "timestamp": to_utc_iso(row["created_at"]),
            "errorDetail": row["reject_reason"],
        }
        for row in rows
    ]


def get_summary() -> Dict[str, Any]:
    """
    Success/error rates and execution metrics, plus per-provider usage.

    Usage figures only cover rows written after the LLM-usage migration; older
    rows have NULL usage and are excluded from the per-provider averages rather
    than counted as zero, which would drag the means down.
    """
    client = get_app_db_client()

    totals, _, _ = client.execute_read(
        """
        SELECT
            COUNT(*) AS total_queries,
            COUNT(*) FILTER (WHERE status = 'success') AS successful_queries,
            COUNT(*) FILTER (WHERE status != 'success') AS failed_queries,
            AVG(exec_time_ms) FILTER (WHERE exec_time_ms IS NOT NULL) AS avg_execution_time_ms
        FROM query_logs
        """
    )
    row = totals[0]
    total = row["total_queries"] or 0

    by_status, _, _ = client.execute_read(
        "SELECT status, COUNT(*) AS count FROM query_logs GROUP BY status ORDER BY count DESC"
    )

    # The usage columns arrive with migrations/20260727_add_llm_usage_to_query_logs.sql.
    # Until that has been applied the columns don't exist, and a pending
    # migration must not take the whole dashboard down - report "no usage yet"
    # and let the rest of the summary through.
    try:
        by_provider, _, _ = client.execute_read(
            """
            SELECT
                model_provider,
                model_name,
                COUNT(*) AS queries,
                SUM(input_tokens) AS input_tokens,
                SUM(output_tokens) AS output_tokens,
                SUM(estimated_cost) AS total_cost,
                AVG(input_tokens + output_tokens) AS avg_tokens_per_query,
                AVG(llm_latency_ms) AS avg_llm_latency_ms
            FROM query_logs
            WHERE model_provider IS NOT NULL AND input_tokens IS NOT NULL
            GROUP BY model_provider, model_name
            ORDER BY queries DESC
            """
        )
    except Exception as e:
        logger.warning(
            f"LLM usage columns unavailable, reporting empty usage "
            f"(has the query_logs usage migration been applied?): {e}"
        )
        by_provider = []

    return {
        "total_queries": total,
        "successful_queries": row["successful_queries"] or 0,
        "failed_queries": row["failed_queries"] or 0,
        "success_rate": (row["successful_queries"] or 0) / total if total else 0.0,
        "error_rate": (row["failed_queries"] or 0) / total if total else 0.0,
        "avg_execution_time_ms": float(row["avg_execution_time_ms"] or 0),
        "status_breakdown": by_status,
        "token_usage_available": bool(by_provider),
        "usage_by_provider": [
            {
                "model_provider": r["model_provider"],
                "model_name": r["model_name"],
                "queries": r["queries"],
                "input_tokens": int(r["input_tokens"] or 0),
                "output_tokens": int(r["output_tokens"] or 0),
                "total_cost": float(r["total_cost"] or 0),
                "avg_tokens_per_query": float(r["avg_tokens_per_query"] or 0),
                "avg_llm_latency_ms": float(r["avg_llm_latency_ms"] or 0),
            }
            for r in by_provider
        ],
    }


def get_query_volume(days: int = 14) -> List[Dict[str, Any]]:
    """Daily query counts over the last `days` days, clamped to a sane window."""
    days = max(1, min(days, MAX_VOLUME_DAYS))
    client = get_app_db_client()

    rows, _, _ = client.execute_read(
        """
        SELECT to_char(date_trunc('day', created_at), 'Mon DD') AS date,
               COUNT(*) AS queries,
               COUNT(*) FILTER (WHERE status = 'success') AS successful
        FROM query_logs
        WHERE created_at >= NOW() - make_interval(days => %s)
        GROUP BY date_trunc('day', created_at)
        ORDER BY date_trunc('day', created_at)
        """,
        (days,)
    )
    return rows


def rerun_logged_query(log_id: str) -> Dict[str, Any]:
    """
    Re-execute a logged SELECT so its live output can be inspected.

    `query_logs` stores the SQL but not the result rows, so output is fetched
    on demand. Only SELECTs are ever re-run - a logged write is never replayed,
    because doing so would mutate the business database a second time.

    Raises:
        ServiceError: 404 when there is no log with that id.
    """
    client = get_app_db_client()

    rows, _, _ = client.execute_read(
        "SELECT sql_generated, status FROM query_logs WHERE id = %s",
        (log_id,)
    )
    if not rows:
        raise ServiceError(404, "Query log not found")

    sql = (rows[0]["sql_generated"] or "").strip()
    if not sql:
        return {"available": False, "reason": "No SQL was recorded for this query."}
    if not sql.lstrip("(").upper().startswith("SELECT"):
        return {
            "available": False,
            "reason": "Live output is only available for read (SELECT) queries.",
        }

    try:
        data, columns, _ = get_supabase_query_executor().execute_with_limit(
            sql, max_rows=MAX_INSPECT_ROWS
        )
        return {"available": True, "columns": columns, "rows": data}
    except Exception as e:
        return {"available": False, "reason": f"Query could not be re-executed: {e}"}
