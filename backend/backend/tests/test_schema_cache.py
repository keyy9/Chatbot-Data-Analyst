"""
Unit tests for the schema-context cache.

The schema context is the only thing the LLM knows about the database - it
never reads a row itself. Before this cache had a lifetime it was filled once
per process and never released, so a table, column or categorical value added
after startup stayed invisible until the backend was restarted, and the model
could not write SQL for a column it was never told about.

A fake client counts introspection calls, so "did it re-read?" is observable
without a database. Time is driven by a stub clock - no sleeping.
"""

import backend.ai.utils.supabase_schema_loader as loader_module
from backend.ai.utils.supabase_schema_loader import SupabaseSchemaLoader


class FakeClient:
    """Counts how many times the schema was actually introspected."""

    def __init__(self):
        self.calls = 0
        self.tables = [{"name": "customers", "columns": []}]

        class _Config:
            schema = "public"

        self.config = _Config()

    def get_all_tables_info(self):
        self.calls += 1
        return self.tables


class StubClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def _loader(monkeypatch, ttl):
    clock = StubClock()
    monkeypatch.setattr(loader_module.time, "monotonic", clock)
    client = FakeClient()
    return SupabaseSchemaLoader(client, ttl_seconds=ttl), client, clock


class TestCacheLifetime:
    def test_first_load_reads_the_database(self, monkeypatch):
        loader, client, _ = _loader(monkeypatch, ttl=300)

        loader.load_schema()

        assert client.calls == 1

    def test_second_load_within_ttl_is_served_from_cache(self, monkeypatch):
        loader, client, clock = _loader(monkeypatch, ttl=300)

        loader.load_schema()
        clock.advance(299)
        loader.load_schema()

        assert client.calls == 1

    def test_load_after_ttl_re_reads_the_database(self, monkeypatch):
        """This is the whole point: a schema change appears without a restart."""
        loader, client, clock = _loader(monkeypatch, ttl=300)

        loader.load_schema()
        clock.advance(301)
        loader.load_schema()

        assert client.calls == 2

    def test_new_table_becomes_visible_after_the_ttl(self, monkeypatch):
        loader, client, clock = _loader(monkeypatch, ttl=60)

        loader.load_schema()
        client.tables = client.tables + [{"name": "invoices", "columns": []}]

        assert len(loader.load_schema()["tables"]) == 1, "still cached"

        clock.advance(61)
        names = [t["name"] for t in loader.load_schema()["tables"]]
        assert "invoices" in names

    def test_ttl_of_zero_disables_caching(self, monkeypatch):
        loader, client, _ = _loader(monkeypatch, ttl=0)

        loader.load_schema()
        loader.load_schema()

        assert client.calls == 2

    def test_use_cache_false_always_re_reads(self, monkeypatch):
        loader, client, _ = _loader(monkeypatch, ttl=300)

        loader.load_schema()
        loader.load_schema(use_cache=False)

        assert client.calls == 2


class TestInvalidate:
    def test_invalidate_forces_the_next_read(self, monkeypatch):
        loader, client, _ = _loader(monkeypatch, ttl=300)

        loader.load_schema()
        loader.invalidate()
        loader.load_schema()

        assert client.calls == 2

    def test_invalidate_does_not_read_by_itself(self, monkeypatch):
        """Invalidation is cheap - reloading happens only when asked."""
        loader, client, _ = _loader(monkeypatch, ttl=300)

        loader.load_schema()
        loader.invalidate()

        assert client.calls == 1

    def test_invalidate_before_any_load_is_safe(self, monkeypatch):
        loader, client, _ = _loader(monkeypatch, ttl=300)

        loader.invalidate()

        assert client.calls == 0

    def test_refresh_reads_immediately(self, monkeypatch):
        loader, client, _ = _loader(monkeypatch, ttl=300)

        loader.load_schema()
        loader.refresh_schema()

        assert client.calls == 2
