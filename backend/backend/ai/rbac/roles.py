"""
Role-Based Access Control (RBAC) System.

Manages different roles (User, Admin) dengan permission levels berbeda.
"""

import logging
from enum import Enum
from typing import List, Set, Dict, Optional
from dataclasses import dataclass

# ============ Setup Logging ============
logger = logging.getLogger(__name__)


class Role(Enum):
    """
    Available roles in the system.
    """
    USER = "user"           # Read-only access
    ADMIN = "admin"         # Full CRUD access
    ANALYST = "analyst"     # Read + advanced analytics
    VIEWER = "viewer"       # Limited read access


class Permission(Enum):
    """
    Permission levels.
    """
    # Read operations
    READ = "read"
    
    # Write operations
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    
    # Advanced operations
    SCHEMA_MODIFY = "schema_modify"
    USER_MANAGE = "user_manage"
    EXPORT_DATA = "export_data"
    
    # System operations
    VIEW_LOGS = "view_logs"
    VIEW_MONITORING = "view_monitoring"


@dataclass
class RolePermission:
    """
    Defines permissions for a role.
    
    Attributes:
        role: The role
        permissions: Set of allowed permissions
        allowed_tables: List of tables accessible (None = all tables)
        max_rows: Maximum rows that can be returned (None = unlimited)
    """
    role: Role
    permissions: Set[Permission]
    allowed_tables: Optional[List[str]] = None
    max_rows: Optional[int] = None


class RBACManager:
    """
    Manages role-based access control.
    
    Defines what each role can and cannot do.
    """
    
    # ============ Default Role Permissions ============
    ROLE_PERMISSIONS: Dict[Role, RolePermission] = {
        # User: Read-only, limited rows
        Role.USER: RolePermission(
            role=Role.USER,
            permissions={Permission.READ},
            allowed_tables=None,  # All tables
            max_rows=1000  # Max 1000 rows per query
        ),
        
        # Viewer: Very limited read
        Role.VIEWER: RolePermission(
            role=Role.VIEWER,
            permissions={Permission.READ},
            allowed_tables=None,
            max_rows=100  # Max 100 rows
        ),
        
        # Analyst: Read + export, advanced queries
        Role.ANALYST: RolePermission(
            role=Role.ANALYST,
            permissions={
                Permission.READ,
                Permission.EXPORT_DATA,
                Permission.VIEW_MONITORING
            },
            allowed_tables=None,
            max_rows=10000
        ),
        
        # Admin: Full CRUD + everything
        Role.ADMIN: RolePermission(
            role=Role.ADMIN,
            permissions={
                Permission.READ,
                Permission.CREATE,
                Permission.UPDATE,
                Permission.DELETE,
                Permission.SCHEMA_MODIFY,
                Permission.USER_MANAGE,
                Permission.EXPORT_DATA,
                Permission.VIEW_LOGS,
                Permission.VIEW_MONITORING
            },
            allowed_tables=None,  # All tables
            max_rows=None  # Unlimited
        )
    }
    
    def __init__(self):
        """Initialize RBAC manager."""
        logger.info("RBACManager initialized")
    
    def get_permissions(self, role: Role) -> RolePermission:
        """
        Get permissions for a role.
        
        Args:
            role: The role.
        
        Returns:
            RolePermission: The role's permissions.
        """
        return self.ROLE_PERMISSIONS.get(
            role,
            self.ROLE_PERMISSIONS[Role.VIEWER]  # Default to viewer
        )
    
    def has_permission(self, role: Role, permission: Permission) -> bool:
        """
        Check if role has a specific permission.
        
        Args:
            role: The role.
            permission: The permission to check.
        
        Returns:
            bool: True if role has permission.
        """
        role_perms = self.get_permissions(role)
        return permission in role_perms.permissions
    
    def can_read(self, role: Role) -> bool:
        """Can role read data?"""
        return self.has_permission(role, Permission.READ)
    
    def can_create(self, role: Role) -> bool:
        """Can role create data?"""
        return self.has_permission(role, Permission.CREATE)
    
    def can_update(self, role: Role) -> bool:
        """Can role update data?"""
        return self.has_permission(role, Permission.UPDATE)
    
    def can_delete(self, role: Role) -> bool:
        """Can role delete data?"""
        return self.has_permission(role, Permission.DELETE)
    
    def can_modify_schema(self, role: Role) -> bool:
        """Can role modify schema?"""
        return self.has_permission(role, Permission.SCHEMA_MODIFY)
    
    def get_max_rows(self, role: Role) -> Optional[int]:
        """Get max rows for role."""
        return self.get_permissions(role).max_rows
    
    def get_allowed_tables(self, role: Role) -> Optional[List[str]]:
        """Get allowed tables for role."""
        return self.get_permissions(role).allowed_tables
    
    def get_role_description(self, role: Role) -> str:
        """Get human-readable description of role."""
        descriptions = {
            Role.USER: "Read-only access to database. Limited to 1000 rows per query.",
            Role.VIEWER: "Very limited read-only access. Max 100 rows per query.",
            Role.ANALYST: "Read-only with export and monitoring capabilities. Max 10000 rows.",
            Role.ADMIN: "Full access to all operations including CRUD and schema modification."
        }
        
        return descriptions.get(role, "Unknown role")


# ============ Singleton Instance ============
_rbac_manager: Optional[RBACManager] = None


def get_rbac_manager() -> RBACManager:
    """
    Get or create the global RBAC manager instance.
    
    Returns:
        RBACManager: The RBAC manager instance.
    """
    global _rbac_manager
    if _rbac_manager is None:
        _rbac_manager = RBACManager()
    return _rbac_manager