"""
Supabase Schema Loader.

Fetches database schema directly from Supabase PostgreSQL.
"""

import logging
import time
from typing import Optional, Dict, List, Any

from backend.ai.utils.supabase_client import SupabaseClient, SupabaseConfig
from backend.ai.rbac.table_denylist import APP_INTERNAL_TABLES

# ============ Setup Logging ============
logger = logging.getLogger(__name__)


class SupabaseSchemaLoader:
    """
    Loads database schema from Supabase.
    
    Fetches real schema from information_schema tables.
    Caches results to avoid repeated queries.
    """
    
    def __init__(self, supabase_client: SupabaseClient, ttl_seconds: Optional[int] = None):
        """
        Initialize schema loader.

        Args:
            supabase_client: SupabaseClient instance.
            ttl_seconds: How long a loaded schema stays cached. Defaults to
                `settings.schema_cache_ttl_seconds`; 0 disables caching.
        """
        self.client = supabase_client
        self.schema_cache: Optional[Dict] = None
        self._loaded_at: Optional[float] = None

        if ttl_seconds is None:
            try:
                from backend.ai.config import get_settings
                ttl_seconds = get_settings().schema_cache_ttl_seconds
            except Exception:  # pragma: no cover - config unavailable in isolation
                ttl_seconds = 300
        self.ttl_seconds = ttl_seconds

        logger.info(f"SupabaseSchemaLoader initialized (cache ttl {self.ttl_seconds}s)")

    def _cache_is_fresh(self) -> bool:
        """
        Whether the cached schema may still be served.

        Without this the cache was filled once per process and never released,
        so a table, column or categorical value added after startup stayed
        invisible to the LLM until the backend was restarted - and the model
        cannot write SQL for a column it was never told about.
        """
        if self.schema_cache is None or self._loaded_at is None:
            return False
        if self.ttl_seconds <= 0:  # 0 or negative disables caching entirely
            return False
        return (time.monotonic() - self._loaded_at) < self.ttl_seconds

    def invalidate(self) -> None:
        """
        Drop the cached schema so the next read re-introspects the database.

        Cheaper than `refresh_schema()` - nothing is loaded until something
        actually asks for the schema.
        """
        self.schema_cache = None
        self._loaded_at = None
        logger.info("Schema cache invalidated")

    def load_schema(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        Load complete database schema from Supabase.

        Args:
            use_cache: Whether to use cached schema.

        Returns:
            Dict: Schema information.
        """
        # Return cached if available and not past its TTL
        if use_cache and self._cache_is_fresh():
            return self.schema_cache

        logger.info("Loading schema from Supabase...")

        # Get all tables info. This is the raw truth of DATABASE_URL - every
        # table physically present - which the raw-data browser needs. The
        # app-internal tables are filtered out separately, only where the
        # CHATBOT reads schema (get_schema_definition), so the LLM stays
        # grounded in business data while raw-data browsing sees everything.
        tables = self.client.get_all_tables_info()

        schema = {
            "tables": tables,
            "timestamp": self._get_timestamp(),
            "schema_name": self.client.config.schema
        }
        
        # Cache it, stamped so the TTL can expire it
        self.schema_cache = schema
        self._loaded_at = time.monotonic()

        logger.info(f"Schema loaded: {len(tables)} tables")
        
        return schema
    
    def get_schema_definition(self, use_cache: bool = True) -> str:
        """
        Get formatted schema definition for prompt injection.

        Args:
            use_cache: Whether to use cached schema.

        Returns:
            str: Formatted schema.
        """
        schema = self.load_schema(use_cache=use_cache)

        schema_text = "## DATABASE SCHEMA\n\n"

        for table in schema.get("tables", []):
            table_name = table["name"]
            # Never expose the app's own control-plane tables to the LLM -
            # it must only ever generate SQL against business data. (Raw-data
            # browsing is unaffected; it doesn't go through this method.)
            if table_name.lower() in APP_INTERNAL_TABLES:
                continue
            row_count = self.client.get_table_row_count(table_name)

            schema_text += f"Table: {table_name} (~ {row_count:,} rows)\n"

            for col in table.get("columns", []):
                col_name = col["name"]
                col_type = col["type"]
                nullable = "nullable" if col.get("nullable") else "not null"

                schema_text += f"  - {col_name} ({col_type}) {nullable}\n"

            # Ground the model in REAL categorical values so it filters on
            # exact literals that exist (e.g. status = 'completed', not
            # 'complete'). Only low-cardinality short text columns are shown.
            try:
                hints = self._format_categorical_hints(table_name, table.get("columns", []))
                if hints:
                    schema_text += f"  Example values: {hints}\n"
            except Exception as e:
                logger.warning(f"Failed to build categorical hints for {table_name}: {str(e)}")

            schema_text += "\n"

        return schema_text.strip()

    # Column-type substrings whose literal values don't help SQL generation
    # (numbers/dates/ids/blobs) - only text-like categoricals are useful.
    _NON_CATEGORICAL_TYPES = ("int", "numeric", "real", "double", "float",
                              "timestamp", "date", "time", "bool", "uuid",
                              "json", "bytea", "serial")

    # A column with more distinct values than this is a name or free text, not
    # a category worth listing. One more than the cap is fetched so "more than
    # the cap" can be detected without counting the whole table.
    #
    # Set above the obvious "handful of enum values" mark on purpose: real
    # categoricals here run to 10 (product categories) and 8 (cities), and a
    # tighter cap dropped `products.category` from the prompt entirely - the
    # single most useful grounding list in this schema.
    _MAX_CATEGORICAL_VALUES = 15

    def _format_categorical_hints(self, table_name: str, columns: List[Dict]) -> str:
        """
        List every value of each low-cardinality text column, as 'col: [v1, v2, ...]'.

        These values are what stops the model writing `city = 'jakarta'` against a
        stored `'Jakarta'`, so they have to be COMPLETE and exactly cased. They
        used to be derived from a 25-row sample, which meant a column with 8
        real values could show only 7 - and the model then guessed the casing of
        the one it never saw. `SELECT DISTINCT` per column removes the guesswork.

        Runs once per schema load and is cached with it.
        """
        parts = []

        for col in columns:
            col_name = col["name"]
            col_type = col["type"].lower()
            if any(skip in col_type for skip in self._NON_CATEGORICAL_TYPES):
                continue
            if col_name.lower() == "id" or col_name.lower().endswith("_id"):
                continue

            try:
                rows, _, _ = self.client.execute_read(
                    f'SELECT DISTINCT "{col_name}" AS value FROM "{table_name}" '
                    f'WHERE "{col_name}" IS NOT NULL '
                    f'ORDER BY 1 LIMIT {self._MAX_CATEGORICAL_VALUES + 1}'
                )
            except Exception as e:
                logger.warning(f"Could not read distinct values for {table_name}.{col_name}: {e}")
                continue

            # One over the cap means there are more - a name column, not a category.
            if len(rows) > self._MAX_CATEGORICAL_VALUES:
                continue

            values = [str(r["value"]) for r in rows]
            if not values or any(len(v) > 40 for v in values):
                continue

            parts.append(f"{col_name}: [{', '.join(values)}]")

        return "; ".join(parts)
    
    def get_available_tables(self, use_cache: bool = True) -> List[str]:
        """
        Get list of available tables.
        
        Args:
            use_cache: Whether to use cached schema.
        
        Returns:
            List[str]: Table names.
        """
        schema = self.load_schema(use_cache=use_cache)
        return [table["name"] for table in schema.get("tables", [])]
    
    def get_all_columns_by_table(self, use_cache: bool = True) -> Dict[str, List[str]]:
        """
        Get all columns organized by table.
        
        Args:
            use_cache: Whether to use cached schema.
        
        Returns:
            Dict: Mapping of table name to column names.
        """
        schema = self.load_schema(use_cache=use_cache)
        
        result = {}
        for table in schema.get("tables", []):
            result[table["name"]] = [
                col["name"] for col in table.get("columns", [])
            ]
        
        return result
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """
        Get info for a specific table.
        
        Args:
            table_name: The table name.
        
        Returns:
            Dict: Table information.
        """
        return self.client.get_table_info(table_name)
    
    def get_sample_data(self, table_name: str, limit: int = 5) -> List[Dict]:
        """
        Get sample data from a table.
        
        Args:
            table_name: The table name.
            limit: Number of rows.
        
        Returns:
            List[Dict]: Sample data.
        """
        return self.client.get_sample_data(table_name, limit)
    
    def refresh_schema(self):
        """Force refresh of schema cache, re-reading the database immediately."""
        logger.info("Refreshing schema cache...")
        self.invalidate()
        self.load_schema(use_cache=False)
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.utcnow().isoformat()


# ============ Singleton Instance ============
_supabase_schema_loader: Optional[SupabaseSchemaLoader] = None


def get_supabase_schema_loader(
    supabase_client: Optional[SupabaseClient] = None
) -> SupabaseSchemaLoader:
    """
    Get or create the global Supabase schema loader instance.
    
    Args:
        supabase_client: SupabaseClient instance (required on first call).
    
    Returns:
        SupabaseSchemaLoader: The schema loader instance.
    """
    global _supabase_schema_loader
    
    if _supabase_schema_loader is None:
        if supabase_client is None:
            from backend.ai.utils.supabase_client import get_supabase_client
            supabase_client = get_supabase_client()
        
        _supabase_schema_loader = SupabaseSchemaLoader(supabase_client)
    
    return _supabase_schema_loader