"""
Write-intent detection.

Recognises a question that is asking to CHANGE data rather than read it, so a
read-only caller is turned away before any SQL is generated - the model never
gets the chance to interpret "delete all cancelled orders" as a SELECT.

Lives here rather than inside a route because both the user-facing endpoint and
the routing evaluation must apply the same rule; if only the route had it, the
evaluation would report a system behaviour that does not exist.

Pure functions: no I/O, no LLM.
"""

WRITE_VERBS = ("update", "delete", "insert", "create", "drop", "alter", "truncate")

CHANGE_PATTERNS = (
    "change the", "change total", "change count",
    "change price", "change status", "modify the",
)


def has_write_intent(question: str) -> bool:
    """
    Whether the question is asking to modify data.

    Deliberately conservative - it only fires on an explicit write verb at the
    start, or an explicit "change X to/from Y" phrasing. A question that merely
    mentions the word "update" in passing ("how many orders had a status
    update?") is a read and must stay answerable.

    Args:
        question: The user's natural language question.

    Returns:
        bool: True when the request is a write, and must be refused for a
            read-only caller.
    """
    q = (question or "").lower().strip()

    if any(q.startswith(verb) for verb in WRITE_VERBS):
        return True

    if any(pattern in q for pattern in CHANGE_PATTERNS) and ("to" in q or "from" in q):
        return True

    return False
