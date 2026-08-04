"""
User notes service.

Owns the `user_notes` table: the observations a user saves alongside their
chat sessions. Split out of the route module so the persistence and the
delete-is-idempotent rule live in one place rather than inline in handlers.
"""

import logging
from typing import Any, Dict, List

from backend.ai.utils.supabase_client import get_app_db_client
from backend.api.services.errors import ServiceError

logger = logging.getLogger(__name__)


def _is_malformed_id(error: Exception) -> bool:
    """
    True when Postgres rejected the id itself rather than failing the query.

    A client can hold a locally-created note/session whose id was never a UUID.
    Deleting one of those can't match a row, so it should read as "already
    gone" instead of a server error.
    """
    message = str(error).lower()
    return "uuid" in message or "invalid input syntax" in message


def list_for_user(user_id: str) -> List[Dict[str, Any]]:
    """Return every note belonging to a user, newest first."""
    client = get_app_db_client()
    try:
        rows, _, _ = client.execute_read(
            'SELECT id, title, content, session_id AS "sessionId", '
            'last_modified AS "lastModified" '
            "FROM user_notes WHERE user_id = %s ORDER BY last_modified DESC",
            (user_id,)
        )
        return rows
    except Exception as e:
        raise ServiceError(500, f"Database error: {e}")


def save(note_id: str, user_id: str, title: str, content: str,
         session_id: str, last_modified: int) -> Dict[str, Any]:
    """
    Insert a note, or update it in place when the id already exists.

    Raises:
        ServiceError: 404 if the owning account doesn't exist.
    """
    client = get_app_db_client()

    try:
        owner, _, _ = client.execute_read(
            "SELECT id FROM users WHERE id = %s AND deleted_at IS NULL",
            (user_id,)
        )
    except Exception as e:
        raise ServiceError(500, f"Database error: {e}")

    if not owner:
        raise ServiceError(404, "User account not found")

    try:
        client.execute_write(
            """
            INSERT INTO user_notes (id, user_id, title, content, session_id, last_modified)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                title = EXCLUDED.title,
                content = EXCLUDED.content,
                session_id = EXCLUDED.session_id,
                last_modified = EXCLUDED.last_modified
            RETURNING id
            """,
            (note_id, user_id, title, content, session_id, last_modified)
        )
    except Exception as e:
        raise ServiceError(500, f"Database error: {e}")

    return {"status": "success", "note_id": note_id}


def delete(note_id: str, user_id: str) -> Dict[str, Any]:
    """
    Delete a note. Idempotent - a note that isn't there counts as deleted.

    Scoped by `user_id` so one account can't delete another's note.
    """
    client = get_app_db_client()
    try:
        _, count, _ = client.execute_write(
            "DELETE FROM user_notes WHERE id = %s AND user_id = %s RETURNING id",
            (note_id, user_id)
        )
        return {"status": "success", "deleted": count}
    except Exception as e:
        if _is_malformed_id(e):
            return {"status": "success", "deleted": 0}
        raise ServiceError(500, f"Database error: {e}")
