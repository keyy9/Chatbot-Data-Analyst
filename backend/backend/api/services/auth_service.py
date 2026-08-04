"""
Authentication service.

Owns the account rules the API enforces - password verification, the
failed-attempt lockout, admin OTP issue/confirm, password reset and change -
along with the `users` / `login_otp` queries they need.

Split out of the route module so the rules can be exercised without a running
FastAPI app, and so each route stays a thin translation of one call. Failures
are raised as `AuthError`; `backend.main` maps that to an HTTP response, which
is why nothing here imports fastapi.
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt

from backend.ai.utils.supabase_client import get_app_db_client
from backend.ai.utils.timestamps import to_utc_iso
from backend.api.services.errors import AuthError
from backend.api.services.email_service import (
    generate_otp,
    send_otp_email,
    send_reset_password_email,
)

__all__ = ["AuthError", "login", "verify_otp", "resend_otp", "get_profile",
           "update_profile", "request_password_reset", "reset_password",
           "change_password"]

logger = logging.getLogger(__name__)

FAILED_ATTEMPTS_LOCKOUT_THRESHOLD = 5
LOCKOUT_MINUTES = 15
OTP_EXPIRE_MINUTES = 5
RESET_TOKEN_EXPIRE_MINUTES = 60
MIN_PASSWORD_LENGTH = 8


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    """Postgres `timestamp without time zone` comes back naive; assume UTC."""
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def _profile_of(row: Dict) -> Dict[str, Any]:
    """Shape a `users` row into the profile payload the API returns."""
    return {
        "user_id": str(row["id"]),
        "email": row["email"],
        "username": row.get("username"),
        "role": row["role"],
        "created_at": to_utc_iso(row.get("created_at")),
    }


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _password_matches(plain: str, hashed: Optional[str]) -> bool:
    if not hashed:
        return False
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def _issue_otp(client, user_id, email: str) -> None:
    """Replace any outstanding code with a fresh one and email it."""
    otp_code = generate_otp()

    client.execute_write(
        "DELETE FROM login_otp WHERE user_id = %s AND is_used = false RETURNING id",
        (user_id,)
    )
    client.execute_write(
        """
        INSERT INTO login_otp (user_id, otp_code, expires_at)
        VALUES (%s, %s, %s)
        RETURNING id
        """,
        (user_id, otp_code, _now() + timedelta(minutes=OTP_EXPIRE_MINUTES))
    )

    if not send_otp_email(email, otp_code):
        raise AuthError(500, "Failed to send OTP email, try again")


def _register_failed_attempt(client, user: Dict) -> None:
    """Count a wrong password, locking the account once the threshold is hit."""
    new_failed = (user.get("failed_attempts") or 0) + 1

    if new_failed >= FAILED_ATTEMPTS_LOCKOUT_THRESHOLD:
        client.execute_write(
            "UPDATE users SET failed_attempts = %s, locked_until = %s WHERE id = %s RETURNING id",
            (new_failed, _now() + timedelta(minutes=LOCKOUT_MINUTES), user["id"])
        )
    else:
        client.execute_write(
            "UPDATE users SET failed_attempts = %s WHERE id = %s RETURNING id",
            (new_failed, user["id"])
        )


def login(email: str, password: str) -> Dict[str, Any]:
    """
    Verify email + password.

    Admins get an emailed OTP instead of an immediate identity; regular users
    log in directly.

    Returns:
        Dict: `{"requires_otp": True, "user_id", "message"}` for admins, or
            the full identity for regular users.

    Raises:
        AuthError: 401 wrong credentials, 403 inactive, 423 locked out.
    """
    client = get_app_db_client()
    email = email.strip().lower()

    rows, _, _ = client.execute_read(
        """
        SELECT id, email, username, hashed_password, role, status,
               failed_attempts, locked_until
        FROM users
        WHERE email = %s AND deleted_at IS NULL
        """,
        (email,)
    )

    invalid = AuthError(401, "Invalid email or password")
    if not rows:
        raise invalid

    user = rows[0]

    if user["status"] != "active":
        raise AuthError(403, "Account is inactive or suspended")

    locked_until = _aware(user.get("locked_until"))
    if locked_until and locked_until > _now():
        raise AuthError(
            423,
            f"Account temporarily locked, try again after {locked_until.strftime('%H:%M UTC')}"
        )

    if not _password_matches(password, user["hashed_password"]):
        _register_failed_attempt(client, user)
        raise invalid

    # Successful password check - clear any lockout state.
    client.execute_write(
        "UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = %s RETURNING id",
        (user["id"],)
    )

    if user["role"] == "admin":
        _issue_otp(client, user["id"], user["email"])
        return {
            "requires_otp": True,
            "user_id": str(user["id"]),
            "message": "A one-time code was sent to your email",
        }

    client.execute_write(
        "UPDATE users SET last_login_at = NOW() WHERE id = %s RETURNING id",
        (user["id"],)
    )

    return {
        "requires_otp": False,
        "user_id": str(user["id"]),
        "email": user["email"],
        "username": user.get("username"),
        "role": user["role"],
    }


def verify_otp(user_id: str, otp_code: str) -> Dict[str, Any]:
    """
    Confirm an admin's emailed OTP and complete login.

    Raises:
        AuthError: 401 wrong/expired code, 403 inactive account.
    """
    client = get_app_db_client()

    otp_rows, _, _ = client.execute_read(
        """
        SELECT id FROM login_otp
        WHERE user_id = %s AND otp_code = %s AND is_used = false AND expires_at > NOW()
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (user_id, otp_code)
    )
    if not otp_rows:
        raise AuthError(401, "Invalid or expired OTP code")

    client.execute_write(
        "UPDATE login_otp SET is_used = true WHERE id = %s RETURNING id",
        (otp_rows[0]["id"],)
    )

    user_rows, _, _ = client.execute_read(
        "SELECT id, email, username, role, status FROM users WHERE id = %s",
        (user_id,)
    )
    if not user_rows or user_rows[0]["status"] != "active":
        raise AuthError(403, "Account is inactive or suspended")

    user = user_rows[0]
    client.execute_write(
        "UPDATE users SET last_login_at = NOW() WHERE id = %s RETURNING id",
        (user["id"],)
    )

    return {
        "requires_otp": False,
        "user_id": str(user["id"]),
        "email": user["email"],
        "username": user.get("username"),
        "role": user["role"],
    }


def resend_otp(user_id: str) -> Dict[str, str]:
    """
    Send a fresh OTP, replacing any outstanding one.

    Raises:
        AuthError: 404 unknown user, 403 inactive account.
    """
    client = get_app_db_client()

    rows, _, _ = client.execute_read(
        "SELECT email, status FROM users WHERE id = %s AND deleted_at IS NULL",
        (user_id,)
    )
    if not rows:
        raise AuthError(404, "User not found")
    if rows[0]["status"] != "active":
        raise AuthError(403, "Account is inactive or suspended")

    _issue_otp(client, user_id, rows[0]["email"])

    return {"status": "success", "message": "New OTP sent successfully"}


def get_profile(user_id: str) -> Dict[str, Any]:
    """
    Read an account's profile.

    Raises:
        AuthError: 404 if the account doesn't exist or was deleted.
    """
    client = get_app_db_client()

    rows, _, _ = client.execute_read(
        "SELECT id, email, username, role, created_at FROM users "
        "WHERE id = %s AND deleted_at IS NULL",
        (user_id,)
    )
    if not rows:
        raise AuthError(404, "User account not found")

    return _profile_of(rows[0])


def update_profile(user_id: str, username: str) -> Dict[str, Any]:
    """
    Change an account's display name.

    Raises:
        AuthError: 400 empty name, 404 unknown account.
    """
    username = username.strip()
    if not username:
        raise AuthError(400, "Display name is required")

    client = get_app_db_client()

    rows, _, _ = client.execute_write(
        "UPDATE users SET username = %s WHERE id = %s AND deleted_at IS NULL "
        "RETURNING id, email, username, role, created_at",
        (username, user_id)
    )
    if not rows:
        raise AuthError(404, "User account not found")

    return _profile_of(rows[0])


def request_password_reset(email: str) -> Dict[str, str]:
    """
    Start a self-service reset.

    Always reports the same message whether or not the email is registered,
    so this endpoint can't be used to discover which addresses have accounts.
    """
    client = get_app_db_client()
    email = email.strip().lower()
    generic = {"message": "If that email is registered, a reset link has been sent."}

    rows, _, _ = client.execute_read(
        "SELECT id, email FROM users "
        "WHERE email = %s AND deleted_at IS NULL AND status = 'active'",
        (email,)
    )
    if not rows:
        return generic

    user = rows[0]
    reset_token = secrets.token_urlsafe(32)

    client.execute_write(
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

    return generic


def reset_password(token: str, new_password: str) -> Dict[str, str]:
    """
    Confirm a reset token (self-service or admin-triggered) with a new password.

    Clears the lockout state too - otherwise someone who reset their password
    because they were locked out would still be locked out.

    Raises:
        AuthError: 400 unknown or expired token.
    """
    client = get_app_db_client()

    rows, _, _ = client.execute_read(
        "SELECT id, reset_token_expires FROM users WHERE reset_token = %s",
        (token,)
    )
    if not rows:
        raise AuthError(400, "Invalid or already-used reset token")

    user = rows[0]
    expires = _aware(user.get("reset_token_expires"))
    if not expires or expires < _now():
        raise AuthError(400, "Reset token has expired, request a new one")

    client.execute_write(
        """
        UPDATE users
        SET hashed_password = %s, reset_token = NULL, reset_token_expires = NULL,
            failed_attempts = 0, locked_until = NULL
        WHERE id = %s
        RETURNING id
        """,
        (_hash_password(new_password), user["id"])
    )

    return {"message": "Password reset successfully. You can now log in."}


def change_password(email: str, current_password: str, new_password: str) -> Dict[str, str]:
    """
    Change a password after checking the current one.

    Raises:
        AuthError: 404 unknown account, 400 wrong current password or a new
            password below the minimum length.
    """
    client = get_app_db_client()

    rows, _, _ = client.execute_read(
        "SELECT id, hashed_password FROM users WHERE email = %s",
        (email.strip().lower(),)
    )
    if not rows:
        raise AuthError(404, "User account not found")

    user = rows[0]

    if not _password_matches(current_password, user.get("hashed_password")):
        raise AuthError(400, "Incorrect current password")

    if len(new_password) < MIN_PASSWORD_LENGTH:
        raise AuthError(
            400,
            f"New password must be at least {MIN_PASSWORD_LENGTH} characters long"
        )

    client.execute_write(
        """
        UPDATE users
        SET hashed_password = %s, failed_attempts = 0, locked_until = NULL
        WHERE id = %s
        RETURNING id
        """,
        (_hash_password(new_password), user["id"])
    )

    return {"message": "Password changed successfully"}
