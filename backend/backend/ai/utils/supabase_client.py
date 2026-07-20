"""
Supabase Postgres Client.

Connects directly to the Supabase-hosted PostgreSQL database to execute
SQL and introspect schema. Supabase's PostgREST/REST API (the `supabase-py`
client) cannot run arbitrary SQL - it only supports table-based REST
queries - so query execution goes straight to Postgres over `DATABASE_URL`
using psycopg2. This is still "Supabase as the database"; it's just
reached via its direct Postgres connection instead of the REST layer.
"""

import logging
import time
import asyncio
from typing import Optional, List, Dict, Any, Tuple

import psycopg2
import psycopg2.extras
import psycopg2.pool
from psycopg2 import sql as pg_sql

# ============ Setup Logging ============
logger = logging.getLogger(__name__)


class SupabaseConfig:
    """
    Supabase/Postgres connection configuration.

    Attributes:
        database_url: Direct PostgreSQL connection string (required to run SQL).
        supabase_url: Supabase project REST URL (kept for reference; not used for SQL).
        supabase_key: Supabase API key (kept for reference; not used for SQL).
        schema: Database schema name (default: public).
        timeout: Statement timeout in seconds.
    """

    def __init__(
        self,
        database_url: str,
        supabase_url: str = "",
        supabase_key: str = "",
        schema: str = "public",
        timeout: int = 30
    ):
        self.database_url = database_url
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.schema = schema
        self.timeout = timeout

    def validate(self) -> bool:
        """Validate configuration."""
        if not self.database_url:
            raise ValueError("database_url is required to execute SQL against Supabase")
        return True


class SupabaseClient:
    """
    Executes SQL and introspects schema against Supabase's Postgres database.

    Holds a small pool of persistent connections rather than opening a new
    one per call - Supabase's Supavisor pooler throttles/queues rapid
    connect+disconnect churn, so reconnecting for every single query (even
    a trivial one) can balloon from ~1s to 20s+ once that throttling kicks
    in. The pool is thread-safe so it's fine to share across FastAPI
    requests.
    """

    def __init__(self, config: SupabaseConfig):
        """
        Initialize Supabase client.

        Args:
            config: SupabaseConfig instance.
        """
        config.validate()
        self.config = config
        self._pool = psycopg2.pool.ThreadedConnectionPool(
            1, 5,
            dsn=self.config.database_url,
            sslmode="require",
            connect_timeout=10,
            options=f"-c statement_timeout={int(self.config.timeout * 1000)}"
        )
        logger.info(f"SupabaseClient initialized for schema: {config.schema}")

    def _run(
        self,
        sql,
        params: Optional[tuple] = None,
        readonly: bool = True
    ) -> Tuple[List[Dict], float]:
        """
        Run a statement against Postgres and return (rows, execution_time_ms).

        `sql` may be a plain string or a `psycopg2.sql.Composable` (used
        internally for identifier-safe schema/table interpolation).

        Read-only statements execute inside `SET TRANSACTION READ ONLY`
        as defense-in-depth beyond `SQLGuardValidator` - even if a write
        statement slipped past validation, Postgres itself refuses it here.
        Connections are pooled and reused, so read-only mode is set
        explicitly on every checkout rather than relying on the previous
        state of a reused connection.
        """
        start_time = time.time()
        conn = self._pool.getconn()
        try:
            conn.set_session(readonly=readonly)

            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params)
                rows = cur.fetchall() if cur.description else []

            conn.commit()

            data = [dict(row) for row in rows]
            execution_time = (time.time() - start_time) * 1000
            return data, execution_time

        except Exception:
            conn.rollback()
            raise
        finally:
            self._pool.putconn(conn)

    def execute_query(self, sql: str) -> Tuple[List[Dict], int, float]:
        """
        Execute a read-only SELECT query.

        Args:
            sql: The SQL query to execute.

        Returns:
            Tuple[List[Dict], int, float]: (results, row_count, execution_time_ms)

        Raises:
            Exception: If query execution fails.

        Example:
            data, count, time = client.execute_query(
                "SELECT * FROM products WHERE stock > 10"
            )
        """
        logger.info(f"Executing query: {sql[:100]}...")

        data, execution_time = self._run(sql, readonly=True)

        logger.info(f"Query executed successfully: {len(data)} rows in {execution_time:.0f}ms")

        return data, len(data), execution_time

    def execute_read(self, sql: str, params: Optional[tuple] = None) -> Tuple[List[Dict], int, float]:
        """
        Execute a trusted, parameterized read-only query (internal app
        tables, not LLM-generated SQL - use `execute_query` for that).

        Args:
            sql: Parameterized SQL (`%s` placeholders).
            params: Values to bind to the statement's placeholders.

        Returns:
            Tuple[List[Dict], int, float]: (results, row_count, execution_time_ms)
        """
        data, execution_time = self._run(sql, params=params, readonly=True)
        return data, len(data), execution_time

    async def execute_query_async(self, sql: str) -> Tuple[List[Dict], int, float]:
        """
        Execute a SELECT query asynchronously.

        Args:
            sql: The SQL query to execute.

        Returns:
            Tuple: (results, row_count, execution_time_ms)
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.execute_query, sql)

    def execute_write(
        self,
        sql: str,
        params: Optional[tuple] = None
    ) -> Tuple[List[Dict], int, float]:
        """
        Execute a parameterized INSERT/UPDATE/DELETE statement.

        Expects the statement to include a `RETURNING` clause so the
        affected row(s) can be reported back to the caller.

        Args:
            sql: The parameterized SQL statement (`%s` placeholders).
            params: Values to bind to the statement's placeholders.

        Returns:
            Tuple[List[Dict], int, float]: (returned rows, row_count, execution_time_ms)
        """
        logger.info(f"Executing write: {sql[:100]}...")

        data, execution_time = self._run(sql, params=params, readonly=False)

        logger.info(f"Write executed successfully: {len(data)} row(s) affected in {execution_time:.0f}ms")

        return data, len(data), execution_time

    def render_sql(self, sql: str, params: Optional[tuple] = None) -> str:
        """
        Render a parameterized statement into a fully-inlined SQL string
        (values safely quoted/escaped), without executing it.

        Used by the admin confirm-token flow to store the exact statement
        that will later be executed, for audit/preview purposes.

        Args:
            sql: The parameterized SQL statement (`%s` placeholders).
            params: Values to bind to the statement's placeholders.

        Returns:
            str: The rendered SQL statement.
        """
        conn = self._pool.getconn()
        try:
            with conn.cursor() as cur:
                return cur.mogrify(sql, params).decode("utf-8")
        finally:
            self._pool.putconn(conn)

    def get_tables(self) -> List[str]:
        """
        Get list of tables in the schema.

        Returns:
            List[str]: Table names.
        """
        try:
            query = """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = %s
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """
            data, _ = self._run(query, params=(self.config.schema,))

            tables = [row["table_name"] for row in data]
            logger.info(f"Found {len(tables)} tables in schema {self.config.schema}")

            return tables

        except Exception as e:
            logger.error(f"Failed to get tables: {str(e)}")
            return []

    def get_table_columns(self, table_name: str) -> Dict[str, str]:
        """
        Get columns for a specific table.

        Args:
            table_name: The table name.

        Returns:
            Dict: Column name to data type mapping.
        """
        try:
            query = """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = %s
                AND table_name = %s
                ORDER BY ordinal_position
            """
            data, _ = self._run(query, params=(self.config.schema, table_name))

            return {row["column_name"]: row["data_type"] for row in data}

        except Exception as e:
            logger.error(f"Failed to get columns for {table_name}: {str(e)}")
            return {}

    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """
        Get detailed info about a table.

        Args:
            table_name: The table name.

        Returns:
            Dict: Table info with columns and types.
        """
        try:
            query = """
                SELECT
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = %s
                AND table_name = %s
                ORDER BY ordinal_position
            """
            data, _ = self._run(query, params=(self.config.schema, table_name))

            columns = [
                {
                    "name": row["column_name"],
                    "type": row["data_type"],
                    "nullable": row["is_nullable"] == "YES",
                    "default": row["column_default"]
                }
                for row in data
            ]

            return {
                "name": table_name,
                "columns": columns,
                "column_count": len(columns)
            }

        except Exception as e:
            logger.error(f"Failed to get table info for {table_name}: {str(e)}")
            return {}

    def get_all_tables_info(self) -> List[Dict[str, Any]]:
        """
        Get info for all tables in schema.

        Returns:
            List[Dict]: Info for each table.
        """
        tables = self.get_tables()

        all_info = []
        for table in tables:
            info = self.get_table_info(table)
            if info:
                all_info.append(info)

        return all_info

    def get_table_row_count(self, table_name: str) -> int:
        """
        Get row count for a table.

        Args:
            table_name: The table name.

        Returns:
            int: Row count.
        """
        try:
            query = pg_sql.SQL("SELECT COUNT(*) as count FROM {}.{}").format(
                pg_sql.Identifier(self.config.schema),
                pg_sql.Identifier(table_name)
            )
            data, _ = self._run(query)

            return data[0]["count"] if data else 0

        except Exception as e:
            logger.warning(f"Failed to get row count for {table_name}: {str(e)}")
            return 0

    def get_sample_data(self, table_name: str, limit: int = 5) -> List[Dict]:
        """
        Get sample data from a table.

        Args:
            table_name: The table name.
            limit: Number of rows to fetch.

        Returns:
            List[Dict]: Sample data.
        """
        try:
            query = pg_sql.SQL("SELECT * FROM {}.{} LIMIT %s").format(
                pg_sql.Identifier(self.config.schema),
                pg_sql.Identifier(table_name)
            )
            data, _ = self._run(query, params=(limit,))

            return data

        except Exception as e:
            logger.warning(f"Failed to get sample data for {table_name}: {str(e)}")
            return []

    def test_connection(self) -> bool:
        """
        Test connection to Supabase's Postgres database.

        Returns:
            bool: True if connection successful.
        """
        try:
            self._run("SELECT 1 as connection_test")
            logger.info("Supabase connection test successful")
            return True

        except Exception as e:
            logger.error(f"Supabase connection test failed: {str(e)}")
            return False

    def close(self):
        """Close all pooled connections."""
        self._pool.closeall()


# ============ Singleton Instance ============
_supabase_client: Optional[SupabaseClient] = None


def get_supabase_client(config: Optional[SupabaseConfig] = None) -> SupabaseClient:
    """
    Get or create the global client for the **business/target database**
    (the data users ask NL questions about - schema introspection and
    generated-SQL execution). Backed by `DATABASE_URL`.

    For the app's own control-plane database (users, chat history, query
    logs, benchmark/eval tables, admin audit), use `get_app_db_client()`
    instead - these are typically two different Supabase projects.

    Args:
        config: SupabaseConfig instance (required on first call, unless
            settings already provide DATABASE_URL/SUPABASE_* env vars).

    Returns:
        SupabaseClient: The Supabase client instance.
    """
    global _supabase_client

    if _supabase_client is None:
        if config is None:
            from backend.ai.config import get_settings
            settings = get_settings()

            if not settings.database_url or settings.database_url.startswith("sqlite"):
                raise ValueError(
                    "Supabase configuration required. "
                    "Provide SupabaseConfig or set DATABASE_URL env variable."
                )

            config = SupabaseConfig(
                database_url=settings.database_url,
                supabase_url=settings.supabase_url,
                supabase_key=settings.supabase_key,
                schema=getattr(settings, 'database_schema', 'public'),
                timeout=getattr(settings, 'query_timeout_seconds', 30)
            )

        _supabase_client = SupabaseClient(config)

    return _supabase_client


# ============ App Control-Plane DB Singleton ============
_app_db_client: Optional[SupabaseClient] = None


def get_app_db_client(config: Optional[SupabaseConfig] = None) -> SupabaseClient:
    """
    Get or create the global client for the **app control-plane database**
    (users, chat_sessions/chat_messages, query_logs, system_prompts,
    benchmark_questions, eval_runs/eval_results, admin_action_logs,
    crud_confirm_tokens). Backed by `APP_DATABASE_URL` - a separate
    Supabase project from the business database used for `get_supabase_client()`.

    Args:
        config: SupabaseConfig instance (required on first call, unless
            settings already provide APP_DATABASE_URL).

    Returns:
        SupabaseClient: The app DB client instance.
    """
    global _app_db_client

    if _app_db_client is None:
        if config is None:
            from backend.ai.config import get_settings
            settings = get_settings()

            if not settings.app_database_url:
                raise ValueError(
                    "App control-plane database configuration required. "
                    "Provide SupabaseConfig or set APP_DATABASE_URL env variable."
                )

            config = SupabaseConfig(
                database_url=settings.app_database_url,
                schema=getattr(settings, 'database_schema', 'public'),
                timeout=getattr(settings, 'query_timeout_seconds', 30)
            )

        _app_db_client = SupabaseClient(config)

    return _app_db_client
