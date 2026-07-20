"""
User Lookup.

Verifies a caller-supplied user_id against the real `users` table instead
of trusting whatever role the request claims - defense-in-depth on top of
the route-level RBAC (which route you hit already forces Role.USER vs
Role.ADMIN, but this confirms the user actually exists, is active, and
holds a role consistent with the operation).
"""

import logging
from typing import Dict, Optional

from backend.ai.utils.supabase_client import SupabaseClient

logger = logging.getLogger(__name__)


def get_user(client: SupabaseClient, user_id: str) -> Optional[Dict]:
    """
    Look up a user by id.

    Args:
        client: SupabaseClient instance.
        user_id: The user's id (UUID string).

    Returns:
        Optional[Dict]: {"id", "role", "status"}, or None if not found
            or the id isn't a valid UUID.
    """
    try:
        data, _, _ = client.execute_read(
            "SELECT id, role, status FROM users WHERE id = %s",
            (user_id,)
        )
        return data[0] if data else None
    except Exception as e:
        logger.warning(f"User lookup failed for {user_id}: {str(e)}")
        return None


def verify_role(
    client: SupabaseClient,
    user_id: str,
    allowed_roles: tuple,
    hard: bool = True
) -> Optional[Dict]:
    """
    Verify a user exists, is active, and holds one of the allowed roles.

    Args:
        client: SupabaseClient instance.
        user_id: The user's id.
        allowed_roles: Roles permitted for this operation (e.g. ("admin",)).
        hard: If True, raise PermissionError on any failure. If False, log
            a warning and return None instead (used for lower-stakes,
            read-only paths where we don't want a DB hiccup to block
            an otherwise-valid request).

    Returns:
        Optional[Dict]: The user record if verified.

    Raises:
        PermissionError: If `hard` is True and verification fails.
    """
    user = get_user(client, user_id)

    if not user:
        message = f"Unknown user_id: {user_id}"
    elif user.get("status") != "active":
        message = f"User {user_id} is not active"
    elif user.get("role") not in allowed_roles:
        message = f"User {user_id} does not have required role {allowed_roles}"
    else:
        return user

    if hard:
        raise PermissionError(message)

    logger.warning(f"{message} (soft check, allowing request through)")
    return None
