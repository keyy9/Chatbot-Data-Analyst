"""
Auth Routes.

Email/password login against the app's own `users` table. Returns the
real `user_id` + `role` the frontend needs to call the user/admin routes -
those routes verify `user_id` against this same table via `verify_role`,
so a caller must have logged in here first to get one. No JWT/session
token is issued - the rest of the API is authorized per-request by
re-checking the supplied `user_id` against `users`, so the frontend just
needs to hold onto the id it got back from login/verify-otp.

Admin logins require a second factor: after password verification, a
6-digit OTP is emailed and must be confirmed via `/verify-otp` before a
usable identity is returned. Regular users skip straight to a normal
login response.

Failed attempts increment `users.failed_attempts`; 5 in a row locks the
account for 15 minutes via `users.locked_until`.
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.ai.utils.supabase_client import get_app_db_client
from backend.api.services.email_service import (
    generate_otp,
    send_otp_email,
    send_reset_password_email,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Auth"])

FAILED_ATTEMPTS_LOCKOUT_THRESHOLD = 5
LOCKOUT_MINUTES = 15
OTP_EXPIRE_MINUTES = 5
RESET_TOKEN_EXPIRE_MINUTES = 60


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    requires_otp: bool = False
    user_id: str
    email: str | None = None
    username: str | None = None
    role: str | None = None
    message: str | None = None


class VerifyOtpRequest(BaseModel):
    user_id: str
    otp_code: str


class ResendOtpRequest(BaseModel):
    user_id: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class UpdateProfileRequest(BaseModel):
    user_id: str
    username: str = Field(min_length=1, max_length=100)


def _now():
    return datetime.now(timezone.utc)


def _aware(dt):
    """Postgres `timestamp without time zone` comes back naive; assume UTC."""
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Verify email + password. Admins get an emailed OTP instead of an
    immediate session; regular users log in directly."""
    app_client = get_app_db_client()
    email = request.email.strip().lower()

    data, _, _ = app_client.execute_read(
        """
        SELECT id, email, username, hashed_password, role, status,
               failed_attempts, locked_until
        FROM users
        WHERE email = %s AND deleted_at IS NULL
        """,
        (email,)
    )

    invalid = HTTPException(status_code=401, detail="Invalid email or password")
    if not data:
        raise invalid

    user = data[0]

    if user["status"] != "active":
        raise HTTPException(status_code=403, detail="Account is inactive or suspended")

    locked_until = _aware(user.get("locked_until"))
    if locked_until and locked_until > _now():
        raise HTTPException(
            status_code=423,
            detail=f"Account temporarily locked, try again after {locked_until.strftime('%H:%M UTC')}"
        )

    if not bcrypt.checkpw(request.password.encode("utf-8"), user["hashed_password"].encode("utf-8")):
        new_failed = (user.get("failed_attempts") or 0) + 1
        lock_update = ""
        params = [new_failed]
        if new_failed >= FAILED_ATTEMPTS_LOCKOUT_THRESHOLD:
            lock_update = ", locked_until = %s"
            params.append(_now() + timedelta(minutes=LOCKOUT_MINUTES))
        params.append(user["id"])

        app_client.execute_write(
            f"UPDATE users SET failed_attempts = %s{lock_update} WHERE id = %s RETURNING id",
            tuple(params)
        )
        raise invalid

    # Successful password check - clear any lockout state.
    app_client.execute_write(
        "UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = %s RETURNING id",
        (user["id"],)
    )

    if user["role"] == "admin":
        otp_code = generate_otp()

        app_client.execute_write(
            "DELETE FROM login_otp WHERE user_id = %s AND is_used = false RETURNING id",
            (user["id"],)
        )
        app_client.execute_write(
            """
            INSERT INTO login_otp (user_id, otp_code, expires_at)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (user["id"], otp_code, _now() + timedelta(minutes=OTP_EXPIRE_MINUTES))
        )

        if not send_otp_email(user["email"], otp_code):
            raise HTTPException(status_code=500, detail="Failed to send OTP email, try again")

        return LoginResponse(
            requires_otp=True,
            user_id=str(user["id"]),
            message="A one-time code was sent to your email"
        )

    app_client.execute_write(
        "UPDATE users SET last_login_at = NOW() WHERE id = %s RETURNING id",
        (user["id"],)
    )

    return LoginResponse(
        requires_otp=False, user_id=str(user["id"]), email=user["email"], username=user.get("username"), role=user["role"]
    )


@router.post("/verify-otp", response_model=LoginResponse)
async def verify_otp(request: VerifyOtpRequest):
    """Confirm an admin's emailed OTP and complete login."""
    app_client = get_app_db_client()

    otp_rows, _, _ = app_client.execute_read(
        """
        SELECT id FROM login_otp
        WHERE user_id = %s AND otp_code = %s AND is_used = false AND expires_at > NOW()
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (request.user_id, request.otp_code)
    )
    if not otp_rows:
        raise HTTPException(status_code=401, detail="Invalid or expired OTP code")

    app_client.execute_write(
        "UPDATE login_otp SET is_used = true WHERE id = %s RETURNING id",
        (otp_rows[0]["id"],)
    )

    user_rows, _, _ = app_client.execute_read(
        "SELECT id, email, username, role, status FROM users WHERE id = %s",
        (request.user_id,)
    )
    if not user_rows or user_rows[0]["status"] != "active":
        raise HTTPException(status_code=403, detail="Account is inactive or suspended")

    user = user_rows[0]
    app_client.execute_write(
        "UPDATE users SET last_login_at = NOW() WHERE id = %s RETURNING id",
        (user["id"],)
    )

    return LoginResponse(
        requires_otp=False, user_id=str(user["id"]), email=user["email"], username=user.get("username"), role=user["role"]
    )


@router.post("/resend-otp")
async def resend_otp(request: ResendOtpRequest):
    """Resend a new OTP to the user's email."""
    app_client = get_app_db_client()
    user_rows, _, _ = app_client.execute_read(
        "SELECT email, status FROM users WHERE id = %s AND deleted_at IS NULL",
        (request.user_id,)
    )
    if not user_rows:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user_rows[0]["status"] != "active":
        raise HTTPException(status_code=403, detail="Account is inactive or suspended")
        
    email = user_rows[0]["email"]
    
    otp_code = generate_otp()
    
    # Delete previous unused OTPs for this user
    app_client.execute_write(
        "DELETE FROM login_otp WHERE user_id = %s AND is_used = false RETURNING id",
        (request.user_id,)
    )
    
    # Insert new OTP
    app_client.execute_write(
        """
        INSERT INTO login_otp (user_id, otp_code, expires_at)
        VALUES (%s, %s, %s)
        """,
        (request.user_id, otp_code, _now() + timedelta(minutes=OTP_EXPIRE_MINUTES))
    )
    
    if not send_otp_email(email, otp_code):
        raise HTTPException(status_code=500, detail="Failed to send OTP email, try again")
        
    return {"status": "success", "message": "New OTP sent successfully"}


@router.get("/profile")
async def get_profile(user_id: str):
    """Return the currently authenticated account's profile from the app database."""
    app_client = get_app_db_client()
    rows, _, _ = app_client.execute_read(
        "SELECT id, email, username, role, created_at FROM users WHERE id = %s AND deleted_at IS NULL",
        (user_id,)
    )
    if not rows:
        raise HTTPException(status_code=404, detail="User account not found")
    row = rows[0]
    return {
        "user_id": str(row["id"]), "email": row["email"], "username": row.get("username"),
        "role": row["role"], "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
    }


@router.post("/profile")
async def update_profile(request: UpdateProfileRequest):
    """Update the display name for the signed-in account in the app database."""
    username = request.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Display name is required")

    app_client = get_app_db_client()
    rows, _, _ = app_client.execute_write(
        "UPDATE users SET username = %s WHERE id = %s AND deleted_at IS NULL RETURNING id, email, username, role, created_at",
        (username, request.user_id)
    )
    if not rows:
        raise HTTPException(status_code=404, detail="User account not found")
    row = rows[0]
    return {
        "user_id": str(row["id"]), "email": row["email"], "username": row.get("username"),
        "role": row["role"], "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
    }


@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    """Self-service reset request. Always returns a generic message
    (whether or not the email exists) to avoid leaking which emails are
    registered."""
    app_client = get_app_db_client()
    email = request.email.strip().lower()
    generic_response = {"message": "If that email is registered, a reset link has been sent."}

    data, _, _ = app_client.execute_read(
        "SELECT id, email FROM users WHERE email = %s AND deleted_at IS NULL AND status = 'active'",
        (email,)
    )
    if not data:
        return generic_response

    user = data[0]
    reset_token = secrets.token_urlsafe(32)

    app_client.execute_write(
        """
        UPDATE users
        SET reset_token = %s, reset_token_expires = %s
        WHERE id = %s
        RETURNING id
        """,
        (reset_token, _now() + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES), user["id"])
    )

    if not send_reset_password_email(user["email"], reset_token):
        logger.warning(f"Failed to send reset-password email to user {user['id']}")

    return generic_response


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    """Confirm a reset token (self-service or admin-triggered) with a new password."""
    app_client = get_app_db_client()

    data, _, _ = app_client.execute_read(
        "SELECT id, reset_token_expires FROM users WHERE reset_token = %s",
        (request.token,)
    )
    if not data:
        raise HTTPException(status_code=400, detail="Invalid or already-used reset token")

    user = data[0]
    expires = _aware(user.get("reset_token_expires"))
    if not expires or expires < _now():
        raise HTTPException(status_code=400, detail="Reset token has expired, request a new one")

    new_hashed = bcrypt.hashpw(request.new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    app_client.execute_write(
        """
        UPDATE users
        SET hashed_password = %s, reset_token = NULL, reset_token_expires = NULL,
            failed_attempts = 0, locked_until = NULL
        WHERE id = %s
        RETURNING id
        """,
        (new_hashed, user["id"])
    )

    return {"message": "Password reset successfully. You can now log in."}


class ChangePasswordRequest(BaseModel):
    email: str
    current_password: str
    new_password: str


@router.post("/change-password")
async def change_password(request: ChangePasswordRequest):
    """Change the user's password after validating their current password."""
    app_client = get_app_db_client()

    data, _, _ = app_client.execute_read(
        "SELECT id, hashed_password FROM users WHERE email = %s",
        (request.email.strip().lower(),)
    )
    if not data:
        raise HTTPException(status_code=404, detail="User account not found")

    user = data[0]
    stored_hash = user.get("hashed_password")

    # Verify current password
    if not stored_hash or not bcrypt.checkpw(request.current_password.encode("utf-8"), stored_hash.encode("utf-8")):
        raise HTTPException(status_code=400, detail="Incorrect current password")

    # Check new password length
    if len(request.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters long")

    # Hash and save new password
    new_hashed = bcrypt.hashpw(request.new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    app_client.execute_write(
        """
        UPDATE users
        SET hashed_password = %s, failed_attempts = 0, locked_until = NULL
        WHERE id = %s
        RETURNING id
        """,
        (new_hashed, user["id"])
    )

    return {"message": "Password changed successfully"}
