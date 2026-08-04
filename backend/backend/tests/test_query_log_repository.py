"""
Unit tests for query logging.

Regression cover for a real outage: `log_query` was changed to INSERT the
LLM-usage columns before the migration that creates them had been applied.
Every INSERT then failed, and because logging is best-effort the failure was
swallowed as a warning - so the Query Logs view silently stopped filling and
nothing pointed at the cause.

Logging must survive a pending migration. A fake client stands in for the
database so both states are exercised without one.
"""

import pytest

from backend.ai.monitoring import query_log_repository as repo
from backend.ai.monitoring.query_log_repository import (
    USAGE_COLUMNS,
    has_usage_columns,
    log_query,
    reset_usage_column_cache,
)


class FakeClient:
    """Reports a chosen set of columns and records what was written."""

    def __init__(self, columns=(), read_raises=False, write_raises=False):
        self.columns = list(columns)
        self.read_raises = read_raises
        self.write_raises = write_raises
        self.writes = []

    def execute_read(self, sql, params=None):
        if self.read_raises:
            raise RuntimeError("connection lost")
        rows = [{"column_name": c} for c in self.columns]
        return rows, len(rows), 0.0

    def execute_write(self, sql, params=None):
        if self.write_raises:
            raise RuntimeError("insert failed")
        self.writes.append((" ".join(sql.split()), params))
        return [{"id": "row-id"}], 1, 0.0


@pytest.fixture(autouse=True)
def _clear_probe_cache():
    reset_usage_column_cache()
    yield
    reset_usage_column_cache()


USAGE = {
    "model_name": "llama-3.1-8b-instant",
    "input_tokens": 1500,
    "output_tokens": 120,
    "estimated_cost": 0.00012,
    "llm_latency_ms": 2100.5,
}


def _log(client):
    log_query(
        client,
        user_id="11111111-1111-1111-1111-111111111111",
        session_id="22222222-2222-2222-2222-222222222222",
        nl_query="How many customers are there?",
        sql_generated="SELECT COUNT(*) FROM customers",
        status="success",
        exec_time_ms=12.7,
        model_provider="groq",
        llm_usage=USAGE,
    )


class TestWritesWithoutTheMigration:
    def test_row_is_still_written(self):
        """The outage: a pending migration must not stop logging."""
        client = FakeClient(columns=[])

        _log(client)

        assert len(client.writes) == 1, "the question must still be logged"

    def test_insert_names_only_existing_columns(self):
        client = FakeClient(columns=[])

        _log(client)

        sql, params = client.writes[0]
        for column in USAGE_COLUMNS:
            assert column not in sql
        assert len(params) == 7

    def test_partial_migration_is_treated_as_absent(self):
        """Half the columns is not usable - fall back rather than fail."""
        client = FakeClient(columns=list(USAGE_COLUMNS[:3]))

        _log(client)

        sql, params = client.writes[0]
        assert "input_tokens" not in sql
        assert len(params) == 7


class TestWritesWithTheMigration:
    def test_usage_columns_are_included(self):
        client = FakeClient(columns=list(USAGE_COLUMNS))

        _log(client)

        sql, params = client.writes[0]
        assert "model_provider" in sql
        assert "llm_latency_ms" in sql
        assert len(params) == 13

    def test_usage_values_are_passed_through(self):
        client = FakeClient(columns=list(USAGE_COLUMNS))

        _log(client)

        _, params = client.writes[0]
        assert params[7] == "groq"
        assert params[8] == "llama-3.1-8b-instant"
        assert params[9] == 1500
        assert params[12] == 2100, "latency is stored as a whole millisecond"

    def test_missing_usage_is_written_as_nulls(self):
        """Paths that never call an LLM (raw table browsing) log no usage."""
        client = FakeClient(columns=list(USAGE_COLUMNS))

        log_query(
            client, user_id=None, session_id=None,
            nl_query="[raw table view] customers", sql_generated="SELECT 1",
            status="success",
        )

        _, params = client.writes[0]
        assert params[7] is None
        assert params[9] is None


class TestResilience:
    def test_probe_failure_falls_back_instead_of_losing_the_row(self):
        client = FakeClient(columns=list(USAGE_COLUMNS), read_raises=True)

        _log(client)

        assert len(client.writes) == 1
        assert len(client.writes[0][1]) == 7

    def test_write_failure_never_raises(self):
        """Logging must not turn a good answer into an error response."""
        client = FakeClient(columns=[], write_raises=True)

        _log(client)  # must not raise

    def test_probe_runs_once_per_process(self):
        client = FakeClient(columns=list(USAGE_COLUMNS))

        assert has_usage_columns(client) is True
        client.columns = []  # a later probe would say False
        assert has_usage_columns(client) is True, "result is cached"

    def test_cache_can_be_reset(self):
        client = FakeClient(columns=list(USAGE_COLUMNS))
        assert has_usage_columns(client) is True

        reset_usage_column_cache()
        client.columns = []

        assert has_usage_columns(client) is False
