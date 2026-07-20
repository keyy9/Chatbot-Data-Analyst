"""
System Prompt Store.

Loads the admin-editable system prompt from the `system_prompts` table so
SQL generation rules/tone can be tuned without a code deploy. Falls back
to the hardcoded SQLPromptManager default when the DB has no active row
or the lookup fails for any reason.
"""

import logging
from typing import Optional

from backend.ai.utils.supabase_client import SupabaseClient

logger = logging.getLogger(__name__)


def get_active_system_prompt(client: SupabaseClient) -> Optional[str]:
    """
    Fetch the currently active system prompt.

    Args:
        client: SupabaseClient instance.

    Returns:
        Optional[str]: The active prompt text, or None if unavailable.
    """
    try:
        data, _, _ = client.execute_read(
            "SELECT prompt_text FROM system_prompts WHERE is_active = true "
            "ORDER BY updated_at DESC NULLS LAST LIMIT 1"
        )
        return data[0]["prompt_text"] if data else None
    except Exception as e:
        logger.warning(f"Failed to load active system prompt, using default: {str(e)}")
        return None
