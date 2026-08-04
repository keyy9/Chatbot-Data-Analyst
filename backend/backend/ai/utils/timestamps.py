"""
Timestamp serialisation.

Every timestamp column in the app database is `timestamp without time zone`
holding UTC. Calling `.isoformat()` on one produces a string with no offset
(`2026-07-27T10:07:15`), and both JavaScript's `new Date(...)` and most JSON
clients read an offset-less date-time as LOCAL time. For a reader in UTC+7 that
renders every event seven hours early - a question asked at 17:07 appears in
the UI as 10:07, which reads as "my query was never logged".

Marking the value as UTC on the way out is what makes `toLocaleString()` in the
browser show the right local time.
"""

from datetime import datetime, timezone
from typing import Optional


def to_utc_iso(value: Optional[datetime]) -> Optional[str]:
    """
    Serialise a stored timestamp as an explicitly-UTC ISO 8601 string.

    Args:
        value: A datetime from the database. Naive values are assumed UTC,
            which is how every timestamp column here is written.

    Returns:
        Optional[str]: e.g. `2026-07-27T10:07:15+00:00`, or None.
    """
    if value is None:
        return None

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return value.isoformat()
