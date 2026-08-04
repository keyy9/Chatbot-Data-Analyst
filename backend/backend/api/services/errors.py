"""
Service-layer errors.

Services raise these instead of `HTTPException` so they stay free of FastAPI
and can be exercised without a running app. `backend.main` registers one
handler for `ServiceError`, which covers every subclass.
"""


class ServiceError(Exception):
    """A failure a service wants reported with a specific HTTP status."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class AuthError(ServiceError):
    """An authentication or account failure."""
