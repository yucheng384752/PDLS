"""Authentication and authorization utilities for PDLS"""

from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from .config import settings
from .database import get_db_session

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token handling
security = HTTPBearer()


class TokenType:
    ACCESS = "access"
    REFRESH = "refresh"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token
    
    Args:
        data: Payload data to encode in token
        expires_delta: Token expiration time override
        
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "type": TokenType.ACCESS,
        "iat": datetime.utcnow()
    })
    
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT refresh token
    
    Args:
        data: Payload data to encode in token
        expires_delta: Token expiration time override
        
    Returns:
        Encoded JWT refresh token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "type": TokenType.REFRESH,
        "iat": datetime.utcnow()
    })
    
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def verify_token(token: str, token_type: str = TokenType.ACCESS) -> Optional[dict]:
    """
    Verify and decode JWT token
    
    Args:
        token: JWT token string
        token_type: Expected token type (access/refresh)
        
    Returns:
        Decoded payload if valid, None if invalid
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        
        # Check token type
        if payload.get("type") != token_type:
            return None
            
        # Check expiration
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
            return None
            
        return payload
        
    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        return None


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> int:
    """
    FastAPI dependency to get current user ID from JWT token
    
    Returns:
        User ID from token
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not credentials:
        raise credentials_exception
    
    payload = verify_token(credentials.credentials, TokenType.ACCESS)
    if not payload:
        raise credentials_exception
        
    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception
        
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        raise credentials_exception
        
    # Note: User existence validation will be added when User model is implemented
    return user_id


class RequirePermissions:
    """
    FastAPI dependency to check user permissions
    
    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(
            user_id: int = Depends(get_current_user_id),
            _: None = Depends(RequirePermissions(["admin"]))
        ):
            return {"message": "Admin access granted"}
    """
    
    def __init__(self, required_permissions: list[str]):
        self.required_permissions = required_permissions
    
    async def __call__(
        self,
        user_id: int = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db_session)
    ) -> None:
        """Check if current user has required permissions"""
        # Note: Permission checking will be implemented when User/Permission models are ready
        # For now, just ensure user is authenticated
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )


class RequireRoles:
    """
    FastAPI dependency to check user roles
    
    Usage:
        @router.get("/manager-only")
        async def manager_endpoint(
            user_id: int = Depends(get_current_user_id),
            _: None = Depends(RequireRoles(["manager", "admin"]))
        ):
            return {"message": "Manager access granted"}
    """
    
    def __init__(self, required_roles: list[str]):
        self.required_roles = required_roles
    
    async def __call__(
        self,
        user_id: int = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db_session)
    ) -> None:
        """Check if current user has required roles"""
        # Note: Role checking will be implemented when User/Role models are ready
        # For now, just ensure user is authenticated
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )


# Common permission dependencies
require_admin = RequireRoles(["admin"])
require_manager = RequireRoles(["manager", "admin"])
require_developer = RequireRoles(["developer", "manager", "admin"])
require_viewer = RequireRoles(["viewer", "developer", "manager", "admin"])