"""
Access Control and Authorization System.

Validates user access to resources and operations.
"""

import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

from backend.ai.rbac.roles import Role, Permission, get_rbac_manager
from backend.ai.rbac.table_denylist import APP_INTERNAL_TABLES
from backend.ai.utils.sql_introspection import extract_tables

# ============ Setup Logging ============
logger = logging.getLogger(__name__)


@dataclass
class UserContext:
    """
    User context with role and metadata.
    
    Attributes:
        user_id: User identifier
        role: User's role
        session_id: Session identifier
        organization_id: Organization identifier (optional)
        allowed_tables: Specific tables user can access (optional)
    """
    user_id: str
    role: Role
    session_id: str
    organization_id: Optional[str] = None
    allowed_tables: Optional[list] = None


class AccessControl:
    """
    Manages access control and authorization.
    
    Checks if user can perform specific operations.
    """
    
    def __init__(self):
        """Initialize access control."""
        self.rbac = get_rbac_manager()
        logger.info("AccessControl initialized")
    
    def check_operation_permission(
        self,
        user_context: UserContext,
        operation: str  # "read", "create", "update", "delete"
    ) -> Dict[str, Any]:
        """
        Check if user can perform an operation.
        
        Args:
            user_context: The user context.
            operation: The operation to check (read, create, update, delete).
        
        Returns:
            Dict: {"allowed": bool, "reason": str}
        """
        # Map operation to permission
        permission_map = {
            "read": Permission.READ,
            "create": Permission.CREATE,
            "update": Permission.UPDATE,
            "delete": Permission.DELETE,
            "schema_modify": Permission.SCHEMA_MODIFY
        }
        
        permission = permission_map.get(operation)
        
        if not permission:
            return {
                "allowed": False,
                "reason": f"Unknown operation: {operation}"
            }
        
        # Check permission
        has_permission = self.rbac.has_permission(user_context.role, permission)
        
        if not has_permission:
            return {
                "allowed": False,
                "reason": f"Role {user_context.role.value} does not have {operation} permission"
            }
        
        logger.info(
            f"User {user_context.user_id} (role: {user_context.role.value}) "
            f"authorized for {operation}"
        )
        
        return {"allowed": True, "reason": "Authorized"}
    
    def check_table_access(
        self,
        user_context: UserContext,
        table_name: str
    ) -> Dict[str, Any]:
        """
        Check if user can access a specific table.
        
        Args:
            user_context: The user context.
            table_name: The table name.
        
        Returns:
            Dict: {"allowed": bool, "reason": str}
        """
        # App-internal tables (chat history, notes, auth, eval data, ...) are
        # never reachable via the NL-to-SQL interface, regardless of role -
        # this pipeline only ever answers questions about business data.
        if table_name.lower() in APP_INTERNAL_TABLES:
            return {
                "allowed": False,
                "reason": f"Table '{table_name}' is not accessible via the NL-to-SQL interface"
            }

        # Check role's allowed tables
        allowed_tables = self.rbac.get_allowed_tables(user_context.role)
        
        # If None, user has access to all tables
        if allowed_tables is None:
            # But check user-specific restrictions
            if user_context.allowed_tables and table_name not in user_context.allowed_tables:
                return {
                    "allowed": False,
                    "reason": f"User not allowed to access table: {table_name}"
                }
            
            return {"allowed": True, "reason": "Authorized"}
        
        # Check if table is in allowed list
        if table_name not in allowed_tables:
            return {
                "allowed": False,
                "reason": f"Role {user_context.role.value} not allowed to access {table_name}"
            }
        
        return {"allowed": True, "reason": "Authorized"}
    
    def check_row_limit(
        self,
        user_context: UserContext
    ) -> Optional[int]:
        """
        Get row limit for user.
        
        Args:
            user_context: The user context.
        
        Returns:
            Optional[int]: Max rows allowed (None = unlimited).
        """
        return self.rbac.get_max_rows(user_context.role)
    
    def authorize_sql(
        self,
        user_context: UserContext,
        sql: str
    ) -> Dict[str, Any]:
        """
        Fully authorize a SQL query for a user.
        
        Args:
            user_context: The user context.
            sql: The SQL query.
        
        Returns:
            Dict: Comprehensive authorization result.
        """
        result = {
            "authorized": False,
            "reason": "",
            "warnings": [],
            "checks": {}
        }
        
        sql_upper = sql.upper()
        
        # ============ Detect operation type ============
        if sql_upper.startswith("SELECT"):
            operation = "read"
        elif sql_upper.startswith("INSERT"):
            operation = "create"
        elif sql_upper.startswith("UPDATE"):
            operation = "update"
        elif sql_upper.startswith("DELETE"):
            operation = "delete"
        else:
            result["reason"] = "Unknown SQL operation"
            return result
        
        # ============ Check operation permission ============
        op_check = self.check_operation_permission(user_context, operation)
        result["checks"]["operation"] = op_check
        
        if not op_check["allowed"]:
            result["reason"] = op_check["reason"]
            return result
        
        # ============ Extract tables from SQL ============
        tables = self._extract_tables(sql)
        result["checks"]["tables"] = {"found": tables}
        
        # ============ Check table access ============
        for table in tables:
            table_check = self.check_table_access(user_context, table)
            result["checks"][f"table_{table}"] = table_check
            
            if not table_check["allowed"]:
                result["reason"] = table_check["reason"]
                return result
        
        # ============ Check row limit ============
        max_rows = self.check_row_limit(user_context)
        result["checks"]["row_limit"] = {"limit": max_rows}
        
        # ============ Authorization successful ============
        result["authorized"] = True
        result["reason"] = "Query authorized"
        result["operation"] = operation
        result["max_rows"] = max_rows
        
        logger.info(
            f"Query authorized for {user_context.user_id}: "
            f"operation={operation}, tables={tables}, max_rows={max_rows}"
        )
        
        return result
    
    def _extract_tables(self, sql: str) -> list:
        """Extract table names from SQL."""
        return extract_tables(sql)
    
    def get_user_capabilities(self, user_context: UserContext) -> Dict:
        """
        Get capabilities/permissions for a user.
        
        Args:
            user_context: The user context.
        
        Returns:
            Dict: User capabilities.
        """
        return {
            "user_id": user_context.user_id,
            "role": user_context.role.value,
            "capabilities": {
                "can_read": self.rbac.can_read(user_context.role),
                "can_create": self.rbac.can_create(user_context.role),
                "can_update": self.rbac.can_update(user_context.role),
                "can_delete": self.rbac.can_delete(user_context.role),
                "can_modify_schema": self.rbac.can_modify_schema(user_context.role)
            },
            "limits": {
                "max_rows": self.rbac.get_max_rows(user_context.role)
            },
            "description": self.rbac.get_role_description(user_context.role)
        }


# ============ Singleton Instance ============
_access_control: Optional[AccessControl] = None


def get_access_control() -> AccessControl:
    """
    Get or create the global access control instance.
    
    Returns:
        AccessControl: The access control instance.
    """
    global _access_control
    if _access_control is None:
        _access_control = AccessControl()
    return _access_control