"""
Chat session service.

Owns the user-facing side of `chat_sessions` / `chat_messages`: listing,
creating, renaming and deleting a user's sessions, and rendering a session's
stored messages into the shape the chat UI consumes.

(The pipeline's own writes during a conversation go through
`backend.ai.utils.chat_history`; this module is the CRUD the user drives.)
"""

import json
import logging
from typing import Any, Dict, List, Optional

from backend.ai.utils.supabase_client import get_app_db_client
from backend.api.services.errors import ServiceError
from backend.api.services.notes_service import _is_malformed_id

logger = logging.getLogger(__name__)

CHART_TYPES_WITH_AXES = ("bar", "line", "pie", "area")


def _as_rows(result_json: Any) -> Optional[List[Dict]]:
    """Decode a stored result payload, tolerating a JSON string or NULL."""
    if isinstance(result_json, str):
        try:
            return json.loads(result_json)
        except json.JSONDecodeError:
            return None
    return result_json


def derive_chart_data(chart_type: Optional[str], rows: Any) -> Optional[Dict[str, Any]]:
    """
    Rebuild the axis/series keys a chart needs from the stored rows.

    Only the chart *type* is persisted, not which column is the axis, so the
    keys have to be re-derived on read. Mirrors `deriveAxisFields` in the
    frontend's chartMapping.ts - the two must agree or a reloaded conversation
    renders differently from the live one.

    Pure function: no I/O, so the rule can be tested directly.
    """
    if not chart_type or not isinstance(rows, list) or not rows:
        return None
    if not isinstance(rows[0], dict):
        return None

    normalized = "bar" if chart_type == "column" else chart_type
    if normalized not in CHART_TYPES_WITH_AXES:
        return None

    first_row = rows[0]
    columns = list(first_row.keys())
    # bool is a subclass of int in Python - exclude it or a True/False column
    # would be charted as a numeric series.
    numeric = [
        c for c in columns
        if isinstance(first_row.get(c), (int, float)) and not isinstance(first_row.get(c), bool)
    ]
    if not numeric:
        return None

    non_numeric = [c for c in columns if c not in numeric]
    x_axis_key = non_numeric[0] if non_numeric else columns[0]
    data_keys = [c for c in numeric if c != x_axis_key]
    if not data_keys:
        return None

    return {
        "type": normalized,
        "data": rows,
        "xAxisKey": x_axis_key,
        "dataKeys": data_keys,
    }


def format_message(row: Dict[str, Any]) -> Dict[str, Any]:
    """Render one stored `chat_messages` row into the chat UI's message shape."""
    rows = _as_rows(row.get("result_json"))

    result_preview = None
    if rows and isinstance(rows, list) and rows and isinstance(rows[0], dict):
        result_preview = {"columns": list(rows[0].keys()), "rows": rows}

    status = "Success"
    if (
        row["role"] == "assistant"
        and not row["sql"]
        and not row["needs_clarification"]
        and "error" in (row["text"] or "").lower()
    ):
        status = "Failed"

    return {
        "id": str(row["id"]),
        "sender": "user" if row["role"] == "user" else "ai",
        "text": row["text"],
        "timestamp": int(row["timestamp"].timestamp() * 1000),
        "status": status,
        "sql": row["sql"],
        "isClarification": row["needs_clarification"],
        "clarificationOptions": rows if row["needs_clarification"] else None,
        "resultPreview": result_preview,
        "chartData": derive_chart_data(row.get("chart_type"), rows),
    }


def list_for_user(user_id: str) -> List[Dict[str, Any]]:
    """Return a user's sessions, newest first, with millisecond timestamps."""
    client = get_app_db_client()
    try:
        rows, _, _ = client.execute_read(
            'SELECT id, title, created_at AS "createdAt" '
            "FROM chat_sessions WHERE user_id = %s ORDER BY created_at DESC",
            (user_id,)
        )
    except Exception as e:
        raise ServiceError(500, f"Database error: {e}")

    return [
        {**row, "id": str(row["id"]), "createdAt": int(row["createdAt"].timestamp() * 1000)}
        for row in rows
    ]


def create(session_id: str, user_id: str, title: str) -> Dict[str, str]:
    """Register a session, or retitle it if the client already created it."""
    client = get_app_db_client()
    try:
        client.execute_write(
            "INSERT INTO chat_sessions (id, user_id, title) VALUES (%s, %s, %s) "
            "ON CONFLICT (id) DO UPDATE SET title = EXCLUDED.title RETURNING id",
            (session_id, user_id, title)
        )
    except Exception as e:
        raise ServiceError(500, f"Database error: {e}")

    return {"status": "success", "session_id": session_id}


def rename(session_id: str, user_id: str, title: str) -> Dict[str, str]:
    """
    Retitle a session the caller owns.

    Raises:
        ServiceError: 404 if no session with that id belongs to the caller.
    """
    client = get_app_db_client()
    try:
        _, count, _ = client.execute_write(
            "UPDATE chat_sessions SET title = %s WHERE id = %s AND user_id = %s RETURNING id",
            (title, session_id, user_id)
        )
    except Exception as e:
        raise ServiceError(500, f"Database error: {e}")

    if count == 0:
        raise ServiceError(404, "Session not found or does not belong to you")

    return {"status": "success"}


def delete(session_id: str, user_id: str) -> Dict[str, Any]:
    """
    Delete a session and its messages. Idempotent.

    Whether or not a matching row exists, the caller's intent (this session
    should be gone) is satisfied on return - so a local-only session that was
    never persisted, including one with a legacy non-UUID id, clears from the
    UI instead of reporting a spurious failure.
    """
    client = get_app_db_client()
    try:
        client.execute_write(
            "DELETE FROM chat_messages WHERE session_id = %s",
            (session_id,)
        )
        _, count, _ = client.execute_write(
            "DELETE FROM chat_sessions WHERE id = %s AND user_id = %s RETURNING id",
            (session_id, user_id)
        )
        return {"status": "success", "deleted": count}
    except Exception as e:
        if _is_malformed_id(e):
            return {"status": "success", "deleted": 0}
        raise ServiceError(500, f"Database error: {e}")


def get_messages(session_id: str, user_id: str) -> List[Dict[str, Any]]:
    """
    Return a session's messages, formatted for the chat UI.

    Raises:
        ServiceError: 404 if the session isn't the caller's - checked before
            any message is read, so ownership can't be bypassed by guessing
            a session id.
    """
    client = get_app_db_client()

    owned, _, _ = client.execute_read(
        "SELECT id FROM chat_sessions WHERE id = %s AND user_id = %s",
        (session_id, user_id)
    )
    if not owned:
        raise ServiceError(404, "Session not found or does not belong to you")

    try:
        rows, _, _ = client.execute_read(
            "SELECT id, role, content AS text, sql_generated AS sql, result_json, "
            "chart_type, needs_clarification, created_at AS timestamp "
            "FROM chat_messages WHERE session_id = %s ORDER BY created_at ASC",
            (session_id,)
        )
    except Exception as e:
        raise ServiceError(500, f"Database error: {e}")

    return [format_message(row) for row in rows]
