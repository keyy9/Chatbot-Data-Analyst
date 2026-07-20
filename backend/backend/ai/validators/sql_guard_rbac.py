"""
SQL Guard with RBAC Support.

Enhanced SQL validator that respects role-based access control.
"""

import logging
import re
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from backend.ai.validators.sql_guard import SQLGuardValidator, ValidationError
from backend.ai.rbac.access_control import UserContext, get_access_control
from backend.ai.utils.supabase_client import SupabaseClient

# ============ Setup Logging ============
logger = logging.getLogger(__name__)


class SQLGuardRBAC(SQLGuardValidator):
    """
    SQL Guard with RBAC support.
    
    Allows different SQL operations based on user role:
    - USER: SELECT only (read-only)
    - ADMIN: SELECT, INSERT, UPDATE, DELETE (full CRUD)
    """
    
    # ============ Allowed Statements by Role ============
    ROLE_ALLOWED_STATEMENTS = {
        "user": {"SELECT"},
        "viewer": {"SELECT"},
        "analyst": {"SELECT"},
        "admin": {"SELECT", "INSERT", "UPDATE", "DELETE"}
    }
    
    def __init__(self, strict_mode: bool = True):
        """
        Initialize SQL Guard with RBAC.
        
        Args:
            strict_mode: Whether to be strict with validation.
        """
        super().__init__(strict_mode)
        self.access_control = get_access_control()
        logger.info("SQLGuardRBAC initialized")
    
    def validate_with_rbac(
        self,
        sql_query: str,
        user_context: UserContext
    ) -> Dict:
        """
        Validate SQL query with role-based access control.
        
        Args:
            sql_query: The SQL query to validate.
            user_context: The user context with role.
        
        Returns:
            Dict: Validation result.
        """
        # ============ First: Basic SQL validation ============
        basic_result = self.validate(sql_query)
        
        if not basic_result["is_valid"]:
            return basic_result
        
        # ============ Second: RBAC authorization ============
        auth_result = self.access_control.authorize_sql(
            user_context,
            sql_query
        )
        
        if not auth_result["authorized"]:
            return {
                "is_valid": False,
                "error": auth_result["reason"],
                "error_type": "RBAC_AUTHORIZATION_DENIED",
                "warnings": [],
                "checks_passed": [],
                "rbac_checks": auth_result["checks"]
            }
        
        # ============ Third: Role-specific statement validation ============
        role = user_context.role.value
        allowed_statements = self.ROLE_ALLOWED_STATEMENTS.get(role, {"SELECT"})
        
        sql_upper = sql_query.upper()
        
        for statement in self.FORBIDDEN_STATEMENTS.keys():
            if statement not in allowed_statements:
                if re.search(rf'\b{statement}\b', sql_upper):
                    return {
                        "is_valid": False,
                        "error": f"{statement} not allowed for role {role}",
                        "error_type": "RBAC_STATEMENT_NOT_ALLOWED",
                        "warnings": [],
                        "checks_passed": []
                    }
        
        # ============ Fourth: Add row limit if needed ============
        max_rows = auth_result.get("max_rows")
        
        result = {
            "is_valid": True,
            "error": None,
            "error_type": None,
            "warnings": [],
            "checks_passed": basic_result.get("checks_passed", []),
            "max_rows": max_rows,
            "user_role": role,
            "operation": auth_result.get("operation")
        }
        
        return result


class AdminQueryBuilder:
    """
    Builds safe, parameterized CRUD statements for admin users.

    Returns (sql, params) tuples with `%s` placeholders - values are never
    inlined into the SQL text, so there's no manual escaping to get wrong.
    Every statement includes `RETURNING *` so the caller always gets back
    the affected row(s) for confirmation/audit.
    """

    _IDENTIFIER_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

    def __init__(self):
        """Initialize query builder."""
        logger.info("AdminQueryBuilder initialized")

    def _validate_identifier(self, name: str, kind: str) -> None:
        """Validate a table/column name is a safe SQL identifier."""
        if not name or not self._IDENTIFIER_PATTERN.match(name):
            raise ValueError(f"Invalid {kind} name: {name}")

    def build_insert(self, table: str, data: Dict) -> Tuple[str, tuple]:
        """
        Build a parameterized INSERT statement.

        Args:
            table: Table name.
            data: Dict of column:value pairs.

        Returns:
            Tuple[str, tuple]: (sql, params)
        """
        if not table or not data:
            raise ValueError("Table and data required")

        self._validate_identifier(table, "table")

        columns = list(data.keys())
        for col in columns:
            self._validate_identifier(col, "column")

        columns_str = ", ".join(columns)
        placeholders = ", ".join(["%s"] * len(columns))
        params = tuple(data[col] for col in columns)

        sql = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders}) RETURNING *"

        logger.info(f"Built INSERT statement for table: {table}")

        return sql, params

    def build_update(
        self,
        table: str,
        data: Dict,
        where_clause: str
    ) -> Tuple[str, tuple]:
        """
        Build a parameterized UPDATE statement.

        Args:
            table: Table name.
            data: Dict of column:value pairs to update.
            where_clause: WHERE clause (must be provided for safety; may
                not itself contain untrusted values - use `where_params`
                for those via a future extension if needed).

        Returns:
            Tuple[str, tuple]: (sql, params) - params covers only the SET values.
        """
        if not table or not data or not where_clause:
            raise ValueError("Table, data, and WHERE clause required")

        self._validate_identifier(table, "table")

        columns = list(data.keys())
        for col in columns:
            self._validate_identifier(col, "column")

        set_str = ", ".join(f"{col} = %s" for col in columns)
        params = tuple(data[col] for col in columns)

        sql = f"UPDATE {table} SET {set_str} WHERE {where_clause} RETURNING *"

        logger.info(f"Built UPDATE statement for table: {table}")

        return sql, params

    def build_delete(self, table: str, where_clause: str) -> Tuple[str, tuple]:
        """
        Build a DELETE statement.

        Args:
            table: Table name.
            where_clause: WHERE clause (must be provided for safety).

        Returns:
            Tuple[str, tuple]: (sql, params) - params is always empty here
                since the WHERE clause is passed through as literal SQL.
        """
        if not table or not where_clause:
            raise ValueError("Table and WHERE clause required")

        self._validate_identifier(table, "table")

        sql = f"DELETE FROM {table} WHERE {where_clause} RETURNING *"

        logger.info(f"Built DELETE statement for table: {table}")

        return sql, ()


class AdminConfirmationStore:
    """
    Propose -> confirm-token -> execute flow for admin writes.

    Destructive admin operations aren't executed immediately: the fully
    rendered SQL is stored in `crud_confirm_tokens` behind a short-lived,
    single-use token, and only runs once that token is confirmed. This
    gives a human-in-the-loop safety check before any INSERT/UPDATE/DELETE
    actually touches the database.
    """

    def __init__(self, execution_client: SupabaseClient, store_client: SupabaseClient, ttl_minutes: int = 10):
        """
        Initialize the confirmation store.

        Args:
            execution_client: SupabaseClient for the business database the
                write actually targets (renders/executes the SQL).
            store_client: SupabaseClient for the app's control-plane
                database, where `crud_confirm_tokens` lives.
            ttl_minutes: How long a proposed statement stays confirmable.
        """
        self.execution_client = execution_client
        self.store_client = store_client
        self.ttl_minutes = ttl_minutes

    def propose(self, admin_id: Optional[str], sql: str, params: Optional[tuple]) -> Dict:
        """
        Render and store a pending admin statement, returning a confirm token.

        Args:
            admin_id: The proposing admin's user id, if known.
            sql: Parameterized SQL (`%s` placeholders).
            params: Values to bind to the statement's placeholders.

        Returns:
            Dict: {"token", "sql_preview", "expires_at"}
        """
        rendered_sql = self.execution_client.render_sql(sql, params)
        token = secrets.token_urlsafe(24)
        expires_at = datetime.utcnow() + timedelta(minutes=self.ttl_minutes)

        self.store_client.execute_write(
            """
            INSERT INTO crud_confirm_tokens (admin_id, sql_to_execute, token, expires_at)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (admin_id, rendered_sql, token, expires_at)
        )

        logger.info(f"Proposed admin statement pending confirmation (token issued, expires {expires_at.isoformat()})")

        return {
            "token": token,
            "sql_preview": rendered_sql,
            "expires_at": expires_at.isoformat()
        }

    def confirm(self, token: str) -> Tuple[str, list, int]:
        """
        Confirm and execute a previously proposed statement.

        Args:
            token: The confirmation token returned by `propose`.

        Returns:
            Tuple[str, list, int]: (executed_sql, returned_rows, affected_count)

        Raises:
            ValueError: If the token is unknown, already used, or expired.
        """
        data, _, _ = self.store_client.execute_read(
            "SELECT id, sql_to_execute, is_used, expires_at FROM crud_confirm_tokens WHERE token = %s",
            (token,)
        )

        if not data:
            raise ValueError("Unknown confirmation token")

        record = data[0]

        if record["is_used"]:
            raise ValueError("Confirmation token has already been used")

        if record["expires_at"] and record["expires_at"] < datetime.utcnow():
            raise ValueError("Confirmation token has expired")

        sql_to_execute = record["sql_to_execute"]

        rows, row_count, _ = self.execution_client.execute_write(sql_to_execute)

        self.store_client.execute_write(
            "UPDATE crud_confirm_tokens SET is_used = true WHERE id = %s RETURNING id",
            (record["id"],)
        )

        return sql_to_execute, rows, row_count


# ============ Singleton Instances ============
_sql_guard_rbac: Optional[SQLGuardRBAC] = None
_admin_query_builder: Optional[AdminQueryBuilder] = None


def get_sql_guard_rbac(strict_mode: bool = True) -> SQLGuardRBAC:
    """Get or create the global SQL Guard RBAC instance."""
    global _sql_guard_rbac
    if _sql_guard_rbac is None:
        _sql_guard_rbac = SQLGuardRBAC(strict_mode)
    return _sql_guard_rbac


def get_admin_query_builder() -> AdminQueryBuilder:
    """Get or create the global admin query builder instance."""
    global _admin_query_builder
    if _admin_query_builder is None:
        _admin_query_builder = AdminQueryBuilder()
    return _admin_query_builder


_admin_confirmation_store: Optional[AdminConfirmationStore] = None


def get_admin_confirmation_store(
    execution_client: Optional[SupabaseClient] = None,
    store_client: Optional[SupabaseClient] = None
) -> AdminConfirmationStore:
    """Get or create the global admin confirmation store instance."""
    global _admin_confirmation_store
    if _admin_confirmation_store is None:
        if execution_client is None:
            from backend.ai.utils.supabase_client import get_supabase_client
            execution_client = get_supabase_client()
        if store_client is None:
            from backend.ai.utils.supabase_client import get_app_db_client
            store_client = get_app_db_client()
        _admin_confirmation_store = AdminConfirmationStore(execution_client, store_client)
    return _admin_confirmation_store