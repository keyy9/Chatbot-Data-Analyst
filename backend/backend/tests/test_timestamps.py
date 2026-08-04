"""
Unit tests for timestamp serialisation.

Pure function - no database.

Regression cover: every timestamp column here is `timestamp without time zone`
holding UTC, and `.isoformat()` on a naive value emits no offset. Browsers read
an offset-less date-time as LOCAL time, so a reader in UTC+7 saw every event
seven hours early - a question logged at 17:07 showed up as 10:07 in the Query
Logs view, which reads as "it was never logged".
"""

from datetime import datetime, timedelta, timezone

from backend.ai.utils.timestamps import to_utc_iso


class TestToUtcIso:
    def test_naive_value_is_marked_as_utc(self):
        """The whole point: without an offset the browser shifts the time."""
        result = to_utc_iso(datetime(2026, 7, 27, 10, 7, 15))

        assert result == "2026-07-27T10:07:15+00:00"
        assert result.endswith("+00:00")

    def test_an_offset_free_string_is_never_returned(self):
        result = to_utc_iso(datetime(2026, 7, 27, 10, 7, 15))

        assert "+" in result or result.endswith("Z")

    def test_aware_utc_value_is_preserved(self):
        result = to_utc_iso(datetime(2026, 7, 27, 10, 7, 15, tzinfo=timezone.utc))

        assert result == "2026-07-27T10:07:15+00:00"

    def test_non_utc_offset_is_kept_as_given(self):
        """An already-aware value carries its own offset - don't rewrite it."""
        jakarta = timezone(timedelta(hours=7))
        result = to_utc_iso(datetime(2026, 7, 27, 17, 7, 15, tzinfo=jakarta))

        assert result == "2026-07-27T17:07:15+07:00"

    def test_none_stays_none(self):
        assert to_utc_iso(None) is None

    def test_microseconds_survive(self):
        result = to_utc_iso(datetime(2026, 7, 27, 10, 7, 15, 123456))

        assert result.startswith("2026-07-27T10:07:15.123456")

    def test_same_instant_from_naive_and_aware_agree(self):
        naive = to_utc_iso(datetime(2026, 7, 27, 10, 7, 15))
        aware = to_utc_iso(datetime(2026, 7, 27, 10, 7, 15, tzinfo=timezone.utc))

        assert naive == aware
