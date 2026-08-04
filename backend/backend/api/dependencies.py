"""
Shared FastAPI dependencies.

Authorization lives here so every admin route enforces it identically. The
real check is `verify_role` against the `users` table; these wrappers only
adapt it to HTTP (403 instead of PermissionError) and to the two ways
`user_id` reaches a route.
"""

from fastapi import HTTPException

from backend.ai.rbac.access_control import UserContext
from backend.ai.rbac.roles import Role
from backend.ai.rbac.user_lookup import verify_role
from backend.ai.utils.supabase_client import get_app_db_client


def require_admin(user_id: str) -> UserContext:
    """
    Assert the caller is a real, active admin; raise HTTP 403 otherwise.

    Two ways to use it:

    - As a FastAPI dependency on GET routes, where `user_id` is a query
      parameter: `_: UserContext = Depends(require_admin)`.
    - Called directly from POST handlers, where `user_id` arrives inside the
      request body: `require_admin(request.user_id)`.

    Returns a session-less UserContext. Routes that execute SQL and need the
    chat session bound to the context use `require_admin_session` instead.

    Raises:
        HTTPException: 403 if the user is unknown, inactive, or not an admin.
    """
    try:
        verify_role(get_app_db_client(), user_id, allowed_roles=("admin",), hard=True)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    return UserContext(user_id=user_id, role=Role.ADMIN, session_id="")


def require_admin_session(user_id: str, session_id: str) -> UserContext:
    """
    Same admin check, for routes that execute SQL.

    Those routes pass the resulting context to `AccessControl.authorize_sql`,
    which records the session the statement belongs to - so unlike
    `require_admin`, the real `session_id` has to be carried through.
    """
    require_admin(user_id)
    return UserContext(user_id=user_id, role=Role.ADMIN, session_id=session_id)
