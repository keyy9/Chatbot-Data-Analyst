"""
Admin User Management Routes.

CRUD over the app's own `users` table (ADMIN only) - list/create/rename/
suspend/delete regular user accounts, and trigger a password-reset email
for one. Every mutation is recorded in `admin_audit_logs`.

Admin accounts are never manageable through this panel (can't be edited,
suspended, reset, or deleted here) - they still show up in the list, but
`_get_manageable_user` rejects any mutation targeting one. This avoids a
panel giving one admin the ability to lock out or demote another.
"""

import bcrypt
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.ai.rbac.user_lookup import verify_role
from backend.ai.utils.supabase_client import get_app_db_client, SupabaseClient
from backend.api.services.email_service import send_reset_password_email
import secrets
from datetime import datetime, timedelta, timezone

router = APIRouter(prefix="/api/admin/users", tags=["Admin - User Management"])

VALID_STATUSES = ("active", "inactive", "suspended")


def _require_admin(app_client: SupabaseClient, user_id: str) -> None:
    try:
        verify_role(app_client, user_id, allowed_roles=("admin",), hard=True)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


def _get_manageable_user(app_client: SupabaseClient, target_id: str) -> dict:
    """Look up a target user and reject if they don't exist or are an admin."""
    data, _, _ = app_client.execute_read(
        "SELECT id, email, username, role, status, deleted_at FROM users WHERE id = %s",
        (target_id,)
    )
    if not data or data[0]["deleted_at"] is not None:
        raise HTTPException(status_code=404, detail="User not found")
    if data[0]["role"] == "admin":
        raise HTTPException(status_code=403, detail="Admin accounts cannot be managed through this panel")
    return data[0]


def _log_admin_action(app_client: SupabaseClient, admin_id: str, target_user_id: str, action: str, detail: str | None = None) -> None:
    app_client.execute_write(
        """
        INSERT INTO admin_audit_logs (admin_id, target_user_id, action, detail)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """,
        (admin_id, target_user_id, action, detail)
    )


class CreateUserRequest(BaseModel):
    user_id: str
    email: str
    username: str
    password: str = Field(min_length=8)


class UpdateUsernameRequest(BaseModel):
    user_id: str
    target_id: str
    username: str


class UpdateStatusRequest(BaseModel):
    user_id: str
    target_id: str
    status: str


class TargetUserRequest(BaseModel):
    user_id: str
    target_id: str


@router.get("")
async def list_users(user_id: str):
    """List all users (admins included, read-only) with real query stats
    aggregated from `query_logs`."""
    app_client = get_app_db_client()
    _require_admin(app_client, user_id)

    rows, _, _ = app_client.execute_read(
        """
        SELECT
            u.id, u.email, u.username, u.role, u.status,
            u.last_login_at, u.created_at,
            COALESCE(q.total, 0) AS total_queries,
            COALESCE(q.successful, 0) AS successful_queries,
            COALESCE(q.failed, 0) AS failed_queries
        FROM users u
        LEFT JOIN (
            SELECT
                user_id,
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE status = 'success') AS successful,
                COUNT(*) FILTER (WHERE status != 'success') AS failed
            FROM query_logs
            GROUP BY user_id
        ) q ON q.user_id = u.id
        WHERE u.deleted_at IS NULL
        ORDER BY u.created_at DESC
        """
    )

    return {
        "users": [
            {
                "id": str(r["id"]),
                "email": r["email"],
                "username": r["username"],
                "role": r["role"],
                "status": r["status"],
                "last_login_at": r["last_login_at"].isoformat() if r["last_login_at"] else None,
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                "total_queries": r["total_queries"],
                "successful_queries": r["successful_queries"],
                "failed_queries": r["failed_queries"],
            }
            for r in rows
        ]
    }


@router.post("/create")
async def create_user(request: CreateUserRequest):
    """Add a new user account. Role is always 'user' - this panel cannot mint admins."""
    app_client = get_app_db_client()
    _require_admin(app_client, request.user_id)

    email = request.email.strip().lower()
    existing, _, _ = app_client.execute_read("SELECT id FROM users WHERE email = %s", (email,))
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed = bcrypt.hashpw(request.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    rows, _, _ = app_client.execute_write(
        """
        INSERT INTO users (email, username, hashed_password, role, status)
        VALUES (%s, %s, %s, 'user', 'active')
        RETURNING id, email, username, role, status, created_at
        """,
        (email, request.username.strip(), hashed)
    )
    new_user = rows[0]
    _log_admin_action(app_client, request.user_id, str(new_user["id"]), "create_user")

    return {
        "id": str(new_user["id"]),
        "email": new_user["email"],
        "username": new_user["username"],
        "role": new_user["role"],
        "status": new_user["status"],
        "created_at": new_user["created_at"].isoformat(),
    }


@router.post("/update")
async def update_username(request: UpdateUsernameRequest):
    """Rename a non-admin user."""
    app_client = get_app_db_client()
    _require_admin(app_client, request.user_id)
    _get_manageable_user(app_client, request.target_id)

    username = request.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username cannot be empty")

    app_client.execute_write(
        "UPDATE users SET username = %s WHERE id = %s RETURNING id",
        (username, request.target_id)
    )
    _log_admin_action(app_client, request.user_id, request.target_id, "update_username", f"-> {username}")

    return {"message": "Username updated"}


@router.post("/status")
async def update_status(request: UpdateStatusRequest):
    """Activate/deactivate/suspend a non-admin user."""
    app_client = get_app_db_client()
    _require_admin(app_client, request.user_id)
    _get_manageable_user(app_client, request.target_id)

    if request.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Status must be one of {VALID_STATUSES}")

    app_client.execute_write(
        "UPDATE users SET status = %s WHERE id = %s RETURNING id",
        (request.status, request.target_id)
    )
    _log_admin_action(app_client, request.user_id, request.target_id, "update_status", f"-> {request.status}")

    return {"message": f"Status updated to {request.status}"}


@router.post("/reset-password")
async def trigger_reset_password(request: TargetUserRequest):
    """Admin-triggered reset: generates a token and emails the user a reset link
    (does not set the password directly)."""
    app_client = get_app_db_client()
    _require_admin(app_client, request.user_id)
    target = _get_manageable_user(app_client, request.target_id)

    reset_token = secrets.token_urlsafe(32)
    app_client.execute_write(
        """
        UPDATE users
        SET reset_token = %s, reset_token_expires = %s
        WHERE id = %s
        RETURNING id
        """,
        (reset_token, datetime.now(timezone.utc) + timedelta(hours=1), request.target_id)
    )
    _log_admin_action(app_client, request.user_id, request.target_id, "trigger_reset_password")

    if not send_reset_password_email(target["email"], reset_token):
        raise HTTPException(status_code=500, detail="Reset token created, but the email failed to send")

    return {"message": f"Reset link sent to {target['email']}"}


@router.post("/delete")
async def delete_user(request: TargetUserRequest):
    """Soft-delete a non-admin user."""
    app_client = get_app_db_client()
    _require_admin(app_client, request.user_id)
    _get_manageable_user(app_client, request.target_id)

    app_client.execute_write(
        "UPDATE users SET deleted_at = NOW(), status = 'suspended' WHERE id = %s RETURNING id",
        (request.target_id,)
    )
    _log_admin_action(app_client, request.user_id, request.target_id, "delete_user")

    return {"message": "User deleted"}
