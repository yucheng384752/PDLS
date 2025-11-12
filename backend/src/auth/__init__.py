"""Authentication and authorization module for PDLS"""

from .permissions import (
    Permission,
    PermissionChecker,
    UserRole,
    get_current_user,
    get_current_active_user,
    get_admin_user,
    get_manager_user,
    require_permission,
    require_role,
    require_admin,
    require_manager,
    check_resource_ownership,
    check_user_management_permission,
)

__all__ = [
    "Permission",
    "PermissionChecker",
    "UserRole",
    "get_current_user",
    "get_current_active_user",
    "get_admin_user",
    "get_manager_user",
    "require_permission",
    "require_role",
    "require_admin",
    "require_manager",
    "check_resource_ownership",
    "check_user_management_permission",
]