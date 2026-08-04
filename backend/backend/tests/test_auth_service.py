"""
Integration tests for the auth service, against the real Supabase database.

No fakes and no mocked client: every assertion here goes through the same
`get_app_db_client()` the running API uses, and the state changes are verified
by reading the rows back out of Postgres.

Safety: each test gets a throwaway account created in `setup` and hard-deleted
in teardown, so the lockout and password-change paths never touch a real user.
Nothing here emails anyone - the OTP tests insert the `login_otp` row directly
rather than triggering delivery, which is also what keeps them deterministic.

Requires APP_DATABASE_URL (loaded from backend/.env). Skipped if unreachable.
"""

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import pytest

from backend.ai.utils.supabase_client import get_app_db_client
from backend.api.services import auth_service
from backend.api.services.auth_service import AuthError

PASSWORD = "correct-horse-battery"


def _client():
    try:
        return get_app_db_client()
    except Exception as exc:  # pragma: no cover - environment guard
        pytest.skip(f"app database unavailable: {exc}")


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


@pytest.fixture
def account():
    """Create a real throwaway user, yield it, then delete it for good."""
    client = _client()
    email = f"pytest-{uuid.uuid4().hex[:12]}@test.invalid"

    rows, _, _ = client.execute_write(
        """
        INSERT INTO users (email, username, hashed_password, role, status)
        VALUES (%s, %s, %s, 'user', 'active')
        RETURNING id, email, username, role, status
        """,
        (email, "pytest user", _hash(PASSWORD))
    )
    user = rows[0]
    user_id = str(user["id"])

    try:
        yield {"id": user_id, "email": email, "client": client}
    finally:
        client.execute_write(
            "DELETE FROM login_otp WHERE user_id = %s RETURNING id", (user_id,)
        )
        client.execute_write("DELETE FROM users WHERE id = %s RETURNING id", (user_id,))


def _read_user(client, user_id, columns="failed_attempts, locked_until, hashed_password, status"):
    rows, _, _ = client.execute_read(
        f"SELECT {columns} FROM users WHERE id = %s", (user_id,)
    )
    return rows[0]


def _set(client, user_id, **fields):
    assignments = ", ".join(f"{name} = %s" for name in fields)
    client.execute_write(
        f"UPDATE users SET {assignments} WHERE id = %s RETURNING id",
        (*fields.values(), user_id)
    )


class TestLogin:
    def test_correct_password_logs_in(self, account):
        result = auth_service.login(account["email"], PASSWORD)

        assert result["requires_otp"] is False
        assert result["user_id"] == account["id"]
        assert result["role"] == "user"

    def test_wrong_password_is_counted_in_the_database(self, account):
        with pytest.raises(AuthError) as exc:
            auth_service.login(account["email"], "not-the-password")

        assert exc.value.status_code == 401
        assert _read_user(account["client"], account["id"])["failed_attempts"] == 1

    def test_threshold_failure_locks_the_account(self, account):
        _set(account["client"], account["id"],
             failed_attempts=auth_service.FAILED_ATTEMPTS_LOCKOUT_THRESHOLD - 1)

        with pytest.raises(AuthError):
            auth_service.login(account["email"], "not-the-password")

        row = _read_user(account["client"], account["id"])
        assert row["failed_attempts"] == auth_service.FAILED_ATTEMPTS_LOCKOUT_THRESHOLD
        assert row["locked_until"] is not None

    def test_locked_account_is_refused_even_with_the_right_password(self, account):
        _set(account["client"], account["id"],
             locked_until=datetime.now(timezone.utc) + timedelta(minutes=10))

        with pytest.raises(AuthError) as exc:
            auth_service.login(account["email"], PASSWORD)

        assert exc.value.status_code == 423

    def test_expired_lock_no_longer_blocks(self, account):
        _set(account["client"], account["id"],
             locked_until=datetime.now(timezone.utc) - timedelta(minutes=1))

        result = auth_service.login(account["email"], PASSWORD)

        assert result["requires_otp"] is False

    def test_successful_login_clears_lockout_state(self, account):
        _set(account["client"], account["id"], failed_attempts=3)

        auth_service.login(account["email"], PASSWORD)

        row = _read_user(account["client"], account["id"])
        assert row["failed_attempts"] == 0
        assert row["locked_until"] is None

    def test_successful_login_stamps_last_login(self, account):
        auth_service.login(account["email"], PASSWORD)

        row = _read_user(account["client"], account["id"], columns="last_login_at")
        assert row["last_login_at"] is not None

    def test_suspended_account_is_refused(self, account):
        _set(account["client"], account["id"], status="suspended")

        with pytest.raises(AuthError) as exc:
            auth_service.login(account["email"], PASSWORD)

        assert exc.value.status_code == 403

    def test_soft_deleted_account_cannot_log_in(self, account):
        _set(account["client"], account["id"], deleted_at=datetime.now(timezone.utc))

        with pytest.raises(AuthError) as exc:
            auth_service.login(account["email"], PASSWORD)

        assert exc.value.status_code == 401

    def test_unknown_email_gives_the_same_error_as_a_wrong_password(self):
        _client()

        with pytest.raises(AuthError) as exc:
            auth_service.login("definitely-not-registered@test.invalid", "whatever")

        assert exc.value.status_code == 401
        assert exc.value.detail == "Invalid email or password"


class TestVerifyOtp:
    def _insert_otp(self, client, user_id, code, expires_in_minutes=5):
        client.execute_write(
            """
            INSERT INTO login_otp (user_id, otp_code, expires_at)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (user_id, code, datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes))
        )

    def test_valid_code_completes_login(self, account):
        self._insert_otp(account["client"], account["id"], "123456")

        result = auth_service.verify_otp(account["id"], "123456")

        assert result["requires_otp"] is False
        assert result["user_id"] == account["id"]

    def test_code_is_consumed_so_it_cannot_be_replayed(self, account):
        self._insert_otp(account["client"], account["id"], "123456")

        auth_service.verify_otp(account["id"], "123456")

        with pytest.raises(AuthError) as exc:
            auth_service.verify_otp(account["id"], "123456")
        assert exc.value.status_code == 401

    def test_expired_code_is_refused(self, account):
        self._insert_otp(account["client"], account["id"], "654321", expires_in_minutes=-1)

        with pytest.raises(AuthError) as exc:
            auth_service.verify_otp(account["id"], "654321")

        assert exc.value.status_code == 401

    def test_wrong_code_is_refused(self, account):
        self._insert_otp(account["client"], account["id"], "123456")

        with pytest.raises(AuthError) as exc:
            auth_service.verify_otp(account["id"], "000000")

        assert exc.value.status_code == 401


class TestProfile:
    def test_reads_the_real_row(self, account):
        result = auth_service.get_profile(account["id"])

        assert result["user_id"] == account["id"]
        assert result["email"] == account["email"]
        assert result["role"] == "user"

    def test_unknown_account_is_404(self):
        _client()

        with pytest.raises(AuthError) as exc:
            auth_service.get_profile("00000000-0000-0000-0000-000000000000")

        assert exc.value.status_code == 404

    def test_update_persists_the_new_name(self, account):
        auth_service.update_profile(account["id"], "Renamed In Test")

        assert auth_service.get_profile(account["id"])["username"] == "Renamed In Test"

    def test_blank_name_is_refused(self, account):
        with pytest.raises(AuthError) as exc:
            auth_service.update_profile(account["id"], "   ")

        assert exc.value.status_code == 400


class TestPasswordReset:
    def test_unknown_email_reports_the_same_message(self, account):
        """The response must not reveal whether an address is registered."""
        for_known = auth_service.request_password_reset(account["email"])
        for_unknown = auth_service.request_password_reset("nobody@test.invalid")

        assert for_known == for_unknown

    def test_request_stores_a_token(self, account):
        auth_service.request_password_reset(account["email"])

        row = _read_user(account["client"], account["id"],
                         columns="reset_token, reset_token_expires")
        assert row["reset_token"]
        assert row["reset_token_expires"] is not None

    def test_reset_changes_the_password_and_clears_the_lock(self, account):
        _set(account["client"], account["id"],
             reset_token="pytest-token",
             reset_token_expires=datetime.now(timezone.utc) + timedelta(minutes=10),
             failed_attempts=4,
             locked_until=datetime.now(timezone.utc) + timedelta(minutes=10))

        auth_service.reset_password("pytest-token", "brand-new-password")

        row = _read_user(account["client"], account["id"],
                         columns="hashed_password, failed_attempts, locked_until, reset_token")
        assert bcrypt.checkpw(b"brand-new-password", row["hashed_password"].encode())
        assert row["failed_attempts"] == 0
        assert row["locked_until"] is None
        assert row["reset_token"] is None
        # And the new password actually works end to end.
        assert auth_service.login(account["email"], "brand-new-password")["requires_otp"] is False

    def test_expired_token_is_refused(self, account):
        _set(account["client"], account["id"],
             reset_token="pytest-expired",
             reset_token_expires=datetime.now(timezone.utc) - timedelta(minutes=1))

        with pytest.raises(AuthError) as exc:
            auth_service.reset_password("pytest-expired", "brand-new-password")

        assert exc.value.status_code == 400

    def test_unknown_token_is_refused(self):
        _client()

        with pytest.raises(AuthError) as exc:
            auth_service.reset_password("no-such-token", "brand-new-password")

        assert exc.value.status_code == 400


class TestChangePassword:
    def test_wrong_current_password_is_refused(self, account):
        with pytest.raises(AuthError) as exc:
            auth_service.change_password(account["email"], "guess", "brand-new-password")

        assert exc.value.status_code == 400

    def test_short_new_password_is_refused(self, account):
        with pytest.raises(AuthError) as exc:
            auth_service.change_password(account["email"], PASSWORD, "short")

        assert exc.value.status_code == 400

    def test_change_takes_effect(self, account):
        auth_service.change_password(account["email"], PASSWORD, "another-new-password")

        row = _read_user(account["client"], account["id"])
        assert bcrypt.checkpw(b"another-new-password", row["hashed_password"].encode())
        assert auth_service.login(account["email"], "another-new-password")["requires_otp"] is False

    def test_unknown_account_is_404(self):
        _client()

        with pytest.raises(AuthError) as exc:
            auth_service.change_password("nobody@test.invalid", "x", "brand-new-password")

        assert exc.value.status_code == 404
