"""
Admin user-management service.

CRUD over the app's own `users` table on behalf of an admin: list, create,
rename, change status, trigger a password reset, soft-delete. Every mutation
is recorded in `admin_audit_logs`.

Admin accounts are never manageable here - they appear in the listing but
`_get_manageable_user` rejects any mutation targeting one, so the panel can't
be used by one admin to lock out or demote another.

Split out of the route module so these rules sit next to each other instead of
inside handlers, and so the authorization checks are exercisable directly.
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import bcrypt

from backend.ai.utils.supabase_client import SupabaseClient, get_app_db_client
from backend.ai.utils.timestamps import to_utc_iso
from backend.api.services.email_service import send_reset_password_email
from backend.api.services.errors import ServiceError

logger = logging.getLogger(__name__)

VALID_STATUSES = ("active", "inactive", "suspended")
RESET_TOKEN_EXPIRE_HOURS = 1


def _get_manageable_user(client: SupabaseClient, target_id: str) -> Dict[str, Any]:
    """
    Look up a target account, rejecting one that is missing, deleted, or admin.

    Raises:
        ServiceError: 404 unknown/deleted, 403 when the target is an admin.
    """
    rows, _, _ = client.execute_read(
        "SELECT id, email, username, role, status, deleted_at FROM users WHERE id = %s",
        (target_id,)
    )
    if not rows or rows[0]["deleted_at"] is not None:
        raise ServiceError(404, "User not found")
    if rows[0]["role"] == "admin":
        raise ServiceError(403, "Admin accounts cannot be managed through this panel")
    return rows[0]


def _log_admin_action(client: SupabaseClient, admin_id: str, target_user_id: str,
                      action: str, detail: Optional[str] = None) -> None:
    """Record one admin mutation in the audit trail."""
    client.execute_write(
        """
        INSERT INTO admin_audit_logs (admin_id, target_user_id, action, detail)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """,
        (admin_id, target_user_id, action, detail)
    )


def list_users() -> List[Dict[str, Any]]:
    """List every live account with query stats aggregated from `query_logs`."""
    client = get_app_db_client()

    rows, _, _ = client.execute_read(
        """
        SELECT
            u.id, u.email, u.username, u.role, u.status,
            u.last_login_at, u.created_at,
            -- "Last active" is the later of the last login and the last query
            -- the user actually ran: logging in is not the only thing that
            -- counts as activity, and `query_logs` already timestamps the rest.
            -- Postgres GREATEST ignores NULLs, so a user who has logged in but
            -- never queried (or vice versa) still gets a real timestamp.
            GREATEST(u.last_login_at, q.last_query_at) AS last_active_at,
            COALESCE(q.total, 0) AS total_queries,
            COALESCE(q.successful, 0) AS successful_queries,
            COALESCE(q.failed, 0) AS failed_queries
        FROM users u
        LEFT JOIN (
            SELECT
                user_id,
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE status = 'success') AS successful,
                COUNT(*) FILTER (WHERE status != 'success') AS failed,
                MAX(created_at) AS last_query_at
            FROM query_logs
            GROUP BY user_id
        ) q ON q.user_id = u.id
        WHERE u.deleted_at IS NULL
        ORDER BY u.created_at DESC
        """
    )

    return [
        {
            "id": str(r["id"]),
            "email": r["email"],
            "username": r["username"],
            "role": r["role"],
            "status": r["status"],
            "last_login_at": to_utc_iso(r["last_login_at"]),
            "last_active_at": to_utc_iso(r["last_active_at"]),
            "created_at": to_utc_iso(r["created_at"]),
            "total_queries": r["total_queries"],
            "successful_queries": r["successful_queries"],
            "failed_queries": r["failed_queries"],
        }
        for r in rows
    ]


def create_user(admin_id: str, email: str, username: str, password: str) -> Dict[str, Any]:
    """
    Add an account. Role is always 'user' - this panel cannot mint admins.

    Raises:
        ServiceError: 400 if the email is already registered.
    """
    client = get_app_db_client()
    email = email.strip().lower()

    existing, _, _ = client.execute_read("SELECT id FROM users WHERE email = %s", (email,))
    if existing:
        raise ServiceError(400, "Email already registered")

    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    rows, _, _ = client.execute_write(
        """
        INSERT INTO users (email, username, hashed_password, role, status)
        VALUES (%s, %s, %s, 'user', 'active')
        RETURNING id, email, username, role, status, created_at
        """,
        (email, username.strip(), hashed)
    )
    new_user = rows[0]
    _log_admin_action(client, admin_id, str(new_user["id"]), "create_user")

    return {
        "id": str(new_user["id"]),
        "email": new_user["email"],
        "username": new_user["username"],
        "role": new_user["role"],
        "status": new_user["status"],
        "created_at": to_utc_iso(new_user["created_at"]),
    }


def update_username(admin_id: str, target_id: str, username: str) -> Dict[str, str]:
    """
    Rename a non-admin account.

    Raises:
        ServiceError: 400 empty name, plus whatever `_get_manageable_user` raises.
    """
    client = get_app_db_client()
    _get_manageable_user(client, target_id)

    username = username.strip()
    if not username:
        raise ServiceError(400, "Username cannot be empty")

    client.execute_write(
        "UPDATE users SET username = %s WHERE id = %s RETURNING id",
        (username, target_id)
    )
    _log_admin_action(client, admin_id, target_id, "update_username", f"-> {username}")

    return {"message": "Username updated"}


def update_status(admin_id: str, target_id: str, status: str) -> Dict[str, str]:
    """
    Activate, deactivate or suspend a non-admin account.

    Raises:
        ServiceError: 400 unknown status, plus whatever `_get_manageable_user` raises.
    """
    client = get_app_db_client()
    _get_manageable_user(client, target_id)

    if status not in VALID_STATUSES:
        raise ServiceError(400, f"Status must be one of {VALID_STATUSES}")

    client.execute_write(
        "UPDATE users SET status = %s WHERE id = %s RETURNING id",
        (status, target_id)
    )
    _log_admin_action(client, admin_id, target_id, "update_status", f"-> {status}")

    return {"message": f"Status updated to {status}"}


def trigger_password_reset(admin_id: str, target_id: str) -> Dict[str, str]:
    """
    Issue a reset token and email the user a link.

    Never sets the password directly - the admin only starts the flow.

    Raises:
        ServiceError: 500 if the token was stored but the email failed,
            plus whatever `_get_manageable_user` raises.
    """
    client = get_app_db_client()
    target = _get_manageable_user(client, target_id)

    reset_token = secrets.token_urlsafe(32)
    client.execute_write(
        """
        UPDATE users
        SET reset_token = %s, reset_token_expires = %s
        WHERE id = %s
        RETURNING id
        """,
        (
            reset_token,
            datetime.now(timezone.utc) + timedelta(hours=RESET_TOKEN_EXPIRE_HOURS),
            target_id,
        )
    )
    _log_admin_action(client, admin_id, target_id, "trigger_reset_password")

    if not send_reset_password_email(target["email"], reset_token):
        raise ServiceError(500, "Reset token created, but the email failed to send")

    return {"message": f"Reset link sent to {target['email']}"}


def delete_user(admin_id: str, target_id: str) -> Dict[str, str]:
    """
    Soft-delete a non-admin account.

    The row stays so existing `query_logs` keep a resolvable author; it is
    marked deleted and suspended so it can no longer sign in or be listed.
    """
    client = get_app_db_client()
    _get_manageable_user(client, target_id)

    client.execute_write(
        "UPDATE users SET deleted_at = NOW(), status = 'suspended' WHERE id = %s RETURNING id",
        (target_id,)
    )
    _log_admin_action(client, admin_id, target_id, "delete_user")

    return {"message": "User deleted"}
