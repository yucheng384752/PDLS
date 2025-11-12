"""Role-Based Access Control (RBAC) system for PDLS"""

from typing import Dict, List, Set, Optional, Callable
from functools import wraps
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError, jwt

from ..models.user import UserRole, User
from ..core.database import get_db
from ..core.config import settings

# Security scheme for JWT token
security = HTTPBearer()

# Role hierarchy - higher roles inherit permissions from lower roles
ROLE_HIERARCHY: Dict[UserRole, int] = {
    UserRole.VIEWER: 0,
    UserRole.DEVELOPER: 1,
    UserRole.MANAGER: 2,
    UserRole.ADMIN: 3,
    UserRole.SUPER_ADMIN: 4,
}

# Permission definitions
class Permission:
    """Permission constants for RBAC system"""
    
    # User management
    VIEW_USERS = "view_users"
    CREATE_USERS = "create_users"
    UPDATE_USERS = "update_users"
    DELETE_USERS = "delete_users"
    MANAGE_USER_ROLES = "manage_user_roles"
    
    # Project management
    VIEW_PROJECTS = "view_projects"
    CREATE_PROJECTS = "create_projects"
    UPDATE_PROJECTS = "update_projects"
    DELETE_PROJECTS = "delete_projects"
    MANAGE_PROJECT_MEMBERS = "manage_project_members"
    
    # Development logs
    VIEW_LOGS = "view_logs"
    CREATE_LOGS = "create_logs"
    UPDATE_OWN_LOGS = "update_own_logs"
    UPDATE_ALL_LOGS = "update_all_logs"
    DELETE_OWN_LOGS = "delete_own_logs"
    DELETE_ALL_LOGS = "delete_all_logs"
    
    # System administration
    VIEW_SYSTEM_CONFIG = "view_system_config"
    UPDATE_SYSTEM_CONFIG = "update_system_config"
    VIEW_AUDIT_LOGS = "view_audit_logs"
    MANAGE_BACKUPS = "manage_backups"


# Role-based permissions mapping
ROLE_PERMISSIONS: Dict[UserRole, Set[str]] = {
    UserRole.VIEWER: {
        Permission.VIEW_PROJECTS,
        Permission.VIEW_LOGS,
    },
    
    UserRole.DEVELOPER: {
        Permission.VIEW_PROJECTS,
        Permission.VIEW_LOGS,
        Permission.CREATE_LOGS,
        Permission.UPDATE_OWN_LOGS,
        Permission.DELETE_OWN_LOGS,
    },
    
    UserRole.MANAGER: {
        Permission.VIEW_USERS,
        Permission.VIEW_PROJECTS,
        Permission.CREATE_PROJECTS,
        Permission.UPDATE_PROJECTS,
        Permission.MANAGE_PROJECT_MEMBERS,
        Permission.VIEW_LOGS,
        Permission.CREATE_LOGS,
        Permission.UPDATE_OWN_LOGS,
        Permission.UPDATE_ALL_LOGS,
        Permission.DELETE_OWN_LOGS,
        Permission.DELETE_ALL_LOGS,
    },
    
    UserRole.ADMIN: {
        Permission.VIEW_USERS,
        Permission.CREATE_USERS,
        Permission.UPDATE_USERS,
        Permission.DELETE_USERS,
        Permission.VIEW_PROJECTS,
        Permission.CREATE_PROJECTS,
        Permission.UPDATE_PROJECTS,
        Permission.DELETE_PROJECTS,
        Permission.MANAGE_PROJECT_MEMBERS,
        Permission.VIEW_LOGS,
        Permission.CREATE_LOGS,
        Permission.UPDATE_OWN_LOGS,
        Permission.UPDATE_ALL_LOGS,
        Permission.DELETE_OWN_LOGS,
        Permission.DELETE_ALL_LOGS,
        Permission.VIEW_SYSTEM_CONFIG,
        Permission.VIEW_AUDIT_LOGS,
    },
    
    UserRole.SUPER_ADMIN: {
        Permission.VIEW_USERS,
        Permission.CREATE_USERS,
        Permission.UPDATE_USERS,
        Permission.DELETE_USERS,
        Permission.MANAGE_USER_ROLES,
        Permission.VIEW_PROJECTS,
        Permission.CREATE_PROJECTS,
        Permission.UPDATE_PROJECTS,
        Permission.DELETE_PROJECTS,
        Permission.MANAGE_PROJECT_MEMBERS,
        Permission.VIEW_LOGS,
        Permission.CREATE_LOGS,
        Permission.UPDATE_OWN_LOGS,
        Permission.UPDATE_ALL_LOGS,
        Permission.DELETE_OWN_LOGS,
        Permission.DELETE_ALL_LOGS,
        Permission.VIEW_SYSTEM_CONFIG,
        Permission.UPDATE_SYSTEM_CONFIG,
        Permission.VIEW_AUDIT_LOGS,
        Permission.MANAGE_BACKUPS,
    },
}


class PermissionChecker:
    """Permission checking utility class"""
    
    @staticmethod
    def has_permission(user_role: UserRole, permission: str) -> bool:
        """Check if a role has a specific permission"""
        if user_role not in ROLE_PERMISSIONS:
            return False
        
        return permission in ROLE_PERMISSIONS[user_role]
    
    @staticmethod
    def has_role_level(user_role: UserRole, required_level: UserRole) -> bool:
        """Check if user role meets minimum required level"""
        user_level = ROLE_HIERARCHY.get(user_role, -1)
        required_level_value = ROLE_HIERARCHY.get(required_level, 99)
        
        return user_level >= required_level_value
    
    @staticmethod
    def get_user_permissions(user_role: UserRole) -> Set[str]:
        """Get all permissions for a given role"""
        return ROLE_PERMISSIONS.get(user_role, set())
    
    @staticmethod
    def can_manage_user(current_user_role: UserRole, target_user_role: UserRole) -> bool:
        """Check if current user can manage target user based on role hierarchy"""
        current_level = ROLE_HIERARCHY.get(current_user_role, -1)
        target_level = ROLE_HIERARCHY.get(target_user_role, 99)
        
        # Users can only manage users with lower role levels
        return current_level > target_level


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Dependency to get current authenticated user"""
    token = credentials.credentials
    
    try:
        # 解碼 JWT 令牌
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        user_id = payload.get("sub")
        token_type = payload.get("type")
        
        if not user_id or token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 從數據庫獲取用戶
        query = select(User).where(User.id == int(user_id))
        result = await db.execute(query)
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_permission(permission: str):
    """Decorator to require specific permission for endpoint access"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract current user from dependency
            current_user = None
            for key, value in kwargs.items():
                if isinstance(value, User):
                    current_user = value
                    break
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if not PermissionChecker.has_permission(current_user.role, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required: {permission}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(required_role: UserRole):
    """Decorator to require minimum role level for endpoint access"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract current user from dependency
            current_user = None
            for key, value in kwargs.items():
                if isinstance(value, User):
                    current_user = value
                    break
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if not PermissionChecker.has_role_level(current_user.role, required_role):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient role level. Required: {required_role.value}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_admin():
    """Decorator shortcut for admin-only endpoints"""
    return require_role(UserRole.ADMIN)


def require_manager():
    """Decorator shortcut for manager+ level endpoints"""
    return require_role(UserRole.MANAGER)


# Dependency functions for FastAPI
async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Dependency to get current active user"""
    if current_user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


async def get_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Dependency to ensure user is admin or higher"""
    if not PermissionChecker.has_role_level(current_user.role, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


async def get_manager_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Dependency to ensure user is manager or higher"""
    if not PermissionChecker.has_role_level(current_user.role, UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager privileges required"
        )
    return current_user


def check_resource_ownership(user: User, resource_owner_id: int) -> bool:
    """Check if user owns a resource or has permission to access it"""
    # Owner can always access
    if user.id == resource_owner_id:
        return True
    
    # Managers and above can access others' resources
    return PermissionChecker.has_role_level(user.role, UserRole.MANAGER)


def check_user_management_permission(current_user: User, target_user: User) -> bool:
    """Check if current user can manage target user"""
    # Users can manage themselves (for profile updates)
    if current_user.id == target_user.id:
        return True
    
    # Check role hierarchy for managing other users
    return PermissionChecker.can_manage_user(current_user.role, target_user.role)