"""
Admin User Management Routes.

CRUD over the app's own `users` table (ADMIN only) - list/create/rename/
suspend/delete regular user accounts, and trigger a password-reset email
for one.

The rules (who may be managed, what an audit entry records, which statuses
are valid) live in `backend.api.services.user_management_service`; these
handlers only bind HTTP to it and enforce that the caller is an admin.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.api.dependencies import require_admin
from backend.api.services import user_management_service as service

router = APIRouter(prefix="/api/admin/users", tags=["Admin - User Management"])


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
    require_admin(user_id)
    return {"users": service.list_users()}


@router.post("/create")
async def create_user(request: CreateUserRequest):
    """Add a new user account. Role is always 'user' - this panel cannot mint admins."""
    require_admin(request.user_id)
    return service.create_user(
        request.user_id, request.email, request.username, request.password
    )


@router.post("/update")
async def update_username(request: UpdateUsernameRequest):
    """Rename a non-admin user."""
    require_admin(request.user_id)
    return service.update_username(request.user_id, request.target_id, request.username)


@router.post("/status")
async def update_status(request: UpdateStatusRequest):
    """Activate/deactivate/suspend a non-admin user."""
    require_admin(request.user_id)
    return service.update_status(request.user_id, request.target_id, request.status)


@router.post("/reset-password")
async def trigger_reset_password(request: TargetUserRequest):
    """Admin-triggered reset: generates a token and emails the user a reset link
    (does not set the password directly)."""
    require_admin(request.user_id)
    return service.trigger_password_reset(request.user_id, request.target_id)


@router.post("/delete")
async def delete_user(request: TargetUserRequest):
    """Soft-delete a non-admin user."""
    require_admin(request.user_id)
    return service.delete_user(request.user_id, request.target_id)
