"""User-related Pydantic schemas for API serialization"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator

from src.models.user import UserRole, UserStatus


class UserBase(BaseModel):
    """Base user fields"""
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: EmailStr = Field(..., description="Email address")
    full_name: Optional[str] = Field(None, max_length=100, description="Full name")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    timezone: Optional[str] = Field("UTC", description="User timezone")
    language: Optional[str] = Field("en", description="Preferred language")


class UserCreateRequest(UserBase):
    """Request schema for creating a new user"""
    password: str = Field(..., min_length=8, description="Password")
    role: UserRole = Field(UserRole.DEVELOPER, description="User role")
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        
        if not (has_upper and has_lower and has_digit):
            raise ValueError(
                'Password must contain at least one uppercase letter, '
                'one lowercase letter, and one digit'
            )
        
        return v


class UserUpdateRequest(BaseModel):
    """Request schema for updating user profile"""
    full_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    timezone: Optional[str] = Field(None)
    language: Optional[str] = Field(None)
    status: Optional[UserStatus] = Field(None, description="User status (admin only)")


class UserRoleUpdateRequest(BaseModel):
    """Request schema for updating user role"""
    role: UserRole = Field(..., description="New user role")


class UserResponse(BaseModel):
    """Response schema for user data"""
    id: int
    username: str
    email: str
    full_name: Optional[str]
    phone: Optional[str]
    role: str
    status: str
    timezone: str
    language: str
    email_verified: bool
    last_login_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Response schema for user list with pagination"""
    users: List[UserResponse]
    total: int
    skip: int
    limit: int


class UserPermissionsResponse(BaseModel):
    """Response schema for user permissions"""
    user_id: int
    username: str
    role: str
    permissions: List[str]