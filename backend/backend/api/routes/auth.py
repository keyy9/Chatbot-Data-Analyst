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

The rules themselves (lockout thresholds, OTP lifetime, token expiry) live
in `backend.api.services.auth_service`; these handlers only bind HTTP to it.
`AuthError` is translated to a response by the handler registered in
`backend.main`, so there is no try/except ceremony here.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.api.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["Auth"])


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
    new_password: str = Field(min_length=auth_service.MIN_PASSWORD_LENGTH)


class UpdateProfileRequest(BaseModel):
    user_id: str
    username: str = Field(min_length=1, max_length=100)


class ChangePasswordRequest(BaseModel):
    email: str
    current_password: str
    new_password: str


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Verify email + password. Admins get an emailed OTP instead of an
    immediate session; regular users log in directly."""
    return auth_service.login(request.email, request.password)


@router.post("/verify-otp", response_model=LoginResponse)
async def verify_otp(request: VerifyOtpRequest):
    """Confirm an admin's emailed OTP and complete login."""
    return auth_service.verify_otp(request.user_id, request.otp_code)


@router.post("/resend-otp")
async def resend_otp(request: ResendOtpRequest):
    """Resend a new OTP to the user's email."""
    return auth_service.resend_otp(request.user_id)


@router.get("/profile")
async def get_profile(user_id: str):
    """Return the currently authenticated account's profile."""
    return auth_service.get_profile(user_id)


@router.post("/profile")
async def update_profile(request: UpdateProfileRequest):
    """Update the display name for the signed-in account."""
    return auth_service.update_profile(request.user_id, request.username)


@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    """Self-service reset request. Always returns a generic message
    (whether or not the email exists) to avoid leaking which emails are
    registered."""
    return auth_service.request_password_reset(request.email)


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    """Confirm a reset token (self-service or admin-triggered) with a new password."""
    return auth_service.reset_password(request.token, request.new_password)


@router.post("/change-password")
async def change_password(request: ChangePasswordRequest):
    """Change the user's password after validating their current password."""
    return auth_service.change_password(
        request.email, request.current_password, request.new_password
    )
