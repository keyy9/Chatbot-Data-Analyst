"""
Chat History Repository.

Reads/writes `chat_sessions` and `chat_messages` so the read-only ask
endpoint can support multi-turn conversations: remembering the last
question so a short follow-up answer to a clarification prompt ("this
month", "electronics only") can be merged into a complete question.

All operations are best-effort: a session that doesn't exist yet (e.g.
created by a different part of the app) must not break the chat
response, so failures are caught and logged rather than raised.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from backend.ai.utils.supabase_client import SupabaseClient

logger = logging.getLogger(__name__)


def ensure_session(
    client: SupabaseClient,
    session_id: str,
    user_id: str
) -> None:
    """
    Make sure a `chat_sessions` row exists for this session id before any
    `chat_messages`/`query_logs` row referencing it is written - both have
    a foreign key on `chat_sessions.id`, so a first-message insert would
    otherwise fail silently (best-effort logging swallows the error, but
    history/clarification follow-ups would then never persist).

    Args:
        client: SupabaseClient instance (app control-plane DB).
        session_id: The chat session id (UUID string).
        user_id: The owning user's id (UUID string).
    """
    try:
        client.execute_write(
            """
            INSERT INTO chat_sessions (id, user_id)
            VALUES (%s, %s)
            ON CONFLICT (id) DO NOTHING
            RETURNING id
            """,
            (session_id, user_id)
        )
    except Exception as e:
        logger.warning(f"Failed to ensure chat_sessions row for {session_id}: {str(e)}")


def get_recent_messages(
    client: SupabaseClient,
    session_id: str,
    limit: int = 200
) -> List[Dict[str, Any]]:
    """
    Fetch the most recent messages in a session, oldest first.

    Args:
        client: SupabaseClient instance.
        session_id: The chat session id.
        limit: Maximum number of recent messages to fetch.

    Returns:
        List[Dict]: Recent messages (empty if the session has none, or
            the lookup fails).
    """
    try:
        data, _, _ = client.execute_read(
            """
            SELECT role, content, sql_generated, needs_clarification, created_at
            FROM chat_messages
            WHERE session_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (session_id, limit)
        )
        return list(reversed(data))
    except Exception as e:
        logger.warning(f"Failed to load chat history for session {session_id}: {str(e)}")
        return []


def add_message(
    client: SupabaseClient,
    session_id: str,
    role: str,
    content: str,
    sql_generated: Optional[str] = None,
    result_json: Optional[Any] = None,
    chart_type: Optional[str] = None,
    needs_clarification: bool = False
) -> None:
    """
    Append a message to a chat session.

    Args:
        client: SupabaseClient instance.
        session_id: The chat session id.
        role: "user" or "assistant".
        content: The message text (question or explanation).
        sql_generated: The SQL associated with this turn, if any.
        result_json: The query result data, if any (will be serialized).
        chart_type: The recommended chart type, if any.
        needs_clarification: Whether this assistant turn is a clarification ask.
    """
    try:
        client.execute_write(
            """
            INSERT INTO chat_messages
                (session_id, role, content, sql_generated, result_json, chart_type, needs_clarification)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                session_id,
                role,
                content,
                sql_generated,
                json.dumps(result_json, default=str) if result_json is not None else None,
                chart_type,
                needs_clarification
            )
        )
    except Exception as e:
        logger.warning(f"Failed to append chat message for session {session_id}: {str(e)}")


def resolve_follow_up(
    recent_messages: List[Dict[str, Any]],
    current_question: str,
    merge_fn
) -> str:
    """
    If the last assistant turn asked for clarification, treat the current
    question as the answer and merge it with the prior user question.

    Args:
        recent_messages: Messages from `get_recent_messages`, oldest first.
        current_question: The user's newly submitted question/answer.
        merge_fn: Callable(original_question, clarification_answer) -> str
            (e.g. `ClarificationPromptManager.merge_clarification_with_question`).

    Returns:
        str: The (possibly merged) question to run through SQL generation.
    """
    if not recent_messages:
        return current_question

    last = recent_messages[-1]
    if last.get("role") != "assistant" or not last.get("needs_clarification"):
        return current_question

    # Find the user question that triggered that clarification request.
    for message in reversed(recent_messages[:-1]):
        if message.get("role") == "user":
            return merge_fn(message["content"], current_question)

    return current_question


def build_conversation_context(
    recent_messages: List[Dict[str, Any]],
    current_question: str
) -> str:
    """Return relevant memory for referential follow-up requests.

    Includes the history of user questions, the generated SQL queries, and the
    assistant's natural language explanations, allowing the model to fully
    resolve contextual and referential questions.
    """
    if not recent_messages:
        return ""

    turns = []
    user_msg = None
    for msg in recent_messages:
        role = msg.get("role")
        content = msg.get("content", "")
        if role == "user":
            user_msg = content
        elif role == "assistant" and user_msg:
            sql = msg.get("sql_generated")
            if sql:
                turns.append(f"User: {user_msg}\nGenerated SQL: {sql}\nAssistant Response: {content}")
            else:
                turns.append(f"User: {user_msg}\nAssistant Response: {content}")
            user_msg = None

    if user_msg and (not turns or not turns[-1].startswith(f"User: {user_msg}")):
        turns.append(f"User: {user_msg}")

    if not turns:
        return ""

    lines = "\n\n".join(turns)
    return (
        "## RECENT CONVERSATION HISTORY:\n"
        "Use this history to resolve pronouns (it, them, those, etc.) and follow-up requests.\n"
        "Do not repeat filters from previous queries unless the current request is a follow-up to them.\n\n"
        f"{lines}"
    )
