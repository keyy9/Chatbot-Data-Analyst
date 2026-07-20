"""
Supabase Schema Loader.

Fetches database schema directly from Supabase PostgreSQL.
"""

import logging
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
    
    def __init__(self, supabase_client: SupabaseClient):
        """
        Initialize schema loader.
        
        Args:
            supabase_client: SupabaseClient instance.
        """
        self.client = supabase_client
        self.schema_cache: Optional[Dict] = None
        
        logger.info("SupabaseSchemaLoader initialized")
    
    def load_schema(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        Load complete database schema from Supabase.
        
        Args:
            use_cache: Whether to use cached schema.
        
        Returns:
            Dict: Schema information.
        """
        # Return cached if available
        if use_cache and self.schema_cache:
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
        
        # Cache it
        self.schema_cache = schema
        
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

    def _format_categorical_hints(self, table_name: str, columns: List[Dict]) -> str:
        """
        Summarize low-cardinality text columns as 'col: [v1, v2, v3]'.

        Uses a single sample query per table (cached with the schema), and
        infers "categorical" from the sample: a column showing only a few
        short distinct values is worth grounding; anything with many distinct
        values (names, free text) is high-cardinality and skipped.
        """
        sample_rows = self.get_sample_data(table_name, limit=25)
        if not sample_rows:
            return ""

        parts = []
        for col in columns:
            col_name = col["name"]
            col_type = col["type"].lower()
            if any(skip in col_type for skip in self._NON_CATEGORICAL_TYPES):
                continue
            if col_name.lower() == "id" or col_name.lower().endswith("_id"):
                continue

            distinct = []
            high_cardinality = False
            for row in sample_rows:
                value = row.get(col_name)
                if value is None:
                    continue
                text = str(value)
                if len(text) > 40:  # free-text column (descriptions, notes)
                    high_cardinality = True
                    break
                if text not in distinct:
                    distinct.append(text)
                if len(distinct) > 8:  # too many distinct -> not categorical
                    high_cardinality = True
                    break

            if not high_cardinality and distinct:
                parts.append(f"{col_name}: [{', '.join(distinct)}]")

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
        """Force refresh of schema cache."""
        logger.info("Refreshing schema cache...")
        self.schema_cache = None
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