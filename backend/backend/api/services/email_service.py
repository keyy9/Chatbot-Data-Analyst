"""
Email Service.

Sends OTP (admin login 2FA) and password-reset emails over SMTP. Both
functions return True/False rather than raising - the caller decides
whether a failed send should block the request (it does, for both
current callers in `auth.py`).
"""

import logging
import secrets
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from backend.ai.config import get_settings

logger = logging.getLogger(__name__)


def generate_otp() -> str:
    """6-digit OTP using `secrets` (not `random`) so it isn't predictable."""
    return str(secrets.randbelow(900000) + 100000)


def _send(to_email: str, subject: str, body: str) -> bool:
    settings = get_settings()

    if not settings.smtp_user or not settings.smtp_password:
        logger.error("SMTP not configured (SMTP_USER/SMTP_PASSWORD empty) - cannot send email")
        return False

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_user
    msg["To"] = to_email
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP auth failed - check SMTP_USER/SMTP_PASSWORD (Gmail needs an App Password)")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error sending to {to_email}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending email to {to_email}: {e}")
        return False


def send_otp_email(to_email: str, otp_code: str) -> bool:
    body = f"""Hello,

Your admin login verification code is:

        {otp_code}

This code expires in 5 minutes. Do not share it with anyone.

If you didn't try to log in, ignore this email and consider changing your password.

- Chat with Your Data System
"""
    return _send(to_email, "Admin Login Code - Chat with Your Data", body)


def send_reset_password_email(to_email: str, reset_token: str) -> bool:
    settings = get_settings()
    reset_link = f"{settings.frontend_url}/reset-password?token={reset_token}"

    body = f"""Hello,

A password reset was requested for your account. Click the link below to set a new password:

        {reset_link}

This link expires in 1 hour and can only be used once.

If you didn't request this, ignore this email and your password will remain unchanged.

- Chat with Your Data System
"""
    return _send(to_email, "Reset Your Password - Chat with Your Data", body)
