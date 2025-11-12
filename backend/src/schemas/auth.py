"""Authentication API schemas for PDLS"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, validator
from enum import Enum

from src.models.user import UserRole, UserStatus


class UserRegistrationRequest(BaseModel):
    """用戶註冊請求結構"""
    
    username: str = Field(
        ..., 
        min_length=3, 
        max_length=50,
        description="用戶名（3-50字符，只能包含字母、數字、下劃線、連字符）"
    )
    
    email: EmailStr = Field(
        ...,
        description="電子郵件地址"
    )
    
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="密碼（至少8字符）"
    )
    
    full_name: Optional[str] = Field(
        None,
        max_length=100,
        description="用戶全名"
    )
    
    timezone: str = Field(
        "UTC",
        max_length=50,
        description="用戶時區"
    )
    
    language: str = Field(
        "zh-tw",
        max_length=10,
        description="用戶首選語言"
    )
    
    @validator('username')
    def validate_username(cls, v):
        """驗證用戶名格式"""
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('用戶名只能包含字母、數字、下劃線和連字符')
        return v.lower()
    
    @validator('password')
    def validate_password(cls, v):
        """驗證密碼強度"""
        if len(v) < 8:
            raise ValueError('密碼至少需要8個字符')
        
        # 檢查是否包含至少一個字母和一個數字
        has_letter = any(c.isalpha() for c in v)
        has_digit = any(c.isdigit() for c in v)
        
        if not (has_letter and has_digit):
            raise ValueError('密碼必須包含至少一個字母和一個數字')
        
        return v
    
    @validator('timezone')
    def validate_timezone(cls, v):
        """驗證時區格式"""
        import pytz
        try:
            pytz.timezone(v)
            return v
        except pytz.exceptions.UnknownTimeZoneError:
            raise ValueError(f'無效的時區: {v}')


class UserRegistrationResponse(BaseModel):
    """用戶註冊響應結構"""
    
    id: int
    username: str
    email: str
    full_name: Optional[str]
    status: UserStatus
    is_email_verified: bool
    created_at: datetime
    message: str = "用戶註冊成功，請檢查您的郵箱以驗證帳戶"
    
    class Config:
        from_attributes = True


class UserLoginRequest(BaseModel):
    """用戶登入請求結構"""
    
    username_or_email: str = Field(
        ...,
        description="用戶名或電子郵件地址"
    )
    
    password: str = Field(
        ...,
        description="密碼"
    )
    
    remember_me: bool = Field(
        False,
        description="記住我（延長令牌有效期）"
    )


class TokenResponse(BaseModel):
    """令牌響應結構"""
    
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: 'UserProfile'


class UserProfile(BaseModel):
    """用戶資料結構"""
    
    id: int
    username: str
    email: str
    full_name: Optional[str]
    role: UserRole
    status: UserStatus
    is_email_verified: bool
    avatar_url: Optional[str]
    bio: Optional[str]
    timezone: str
    language: str
    last_login_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PasswordResetRequest(BaseModel):
    """密碼重設請求結構"""
    
    email: EmailStr = Field(
        ...,
        description="註冊的電子郵件地址"
    )


class PasswordResetConfirm(BaseModel):
    """密碼重設確認結構"""
    
    token: str = Field(
        ...,
        description="密碼重設令牌"
    )
    
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="新密碼"
    )
    
    @validator('new_password')
    def validate_new_password(cls, v):
        """驗證新密碼強度"""
        if len(v) < 8:
            raise ValueError('密碼至少需要8個字符')
        
        has_letter = any(c.isalpha() for c in v)
        has_digit = any(c.isdigit() for c in v)
        
        if not (has_letter and has_digit):
            raise ValueError('密碼必須包含至少一個字母和一個數字')
        
        return v


class EmailVerificationRequest(BaseModel):
    """電子郵件驗證請求結構"""
    
    token: str = Field(
        ...,
        description="電子郵件驗證令牌"
    )


class PasswordChangeRequest(BaseModel):
    """密碼更改請求結構"""
    
    current_password: str = Field(
        ...,
        description="當前密碼"
    )
    
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="新密碼"
    )
    
    @validator('new_password')
    def validate_new_password(cls, v):
        """驗證新密碼強度"""
        if len(v) < 8:
            raise ValueError('密碼至少需要8個字符')
        
        has_letter = any(c.isalpha() for c in v)
        has_digit = any(c.isdigit() for c in v)
        
        if not (has_letter and has_digit):
            raise ValueError('密碼必須包含至少一個字母和一個數字')
        
        return v


class UserUpdateRequest(BaseModel):
    """用戶資料更新請求結構"""
    
    full_name: Optional[str] = Field(
        None,
        max_length=100,
        description="用戶全名"
    )
    
    bio: Optional[str] = Field(
        None,
        max_length=500,
        description="用戶簡介"
    )
    
    timezone: Optional[str] = Field(
        None,
        max_length=50,
        description="用戶時區"
    )
    
    language: Optional[str] = Field(
        None,
        max_length=10,
        description="用戶首選語言"
    )
    
    @validator('timezone')
    def validate_timezone(cls, v):
        """驗證時區格式"""
        if v is not None:
            import pytz
            try:
                pytz.timezone(v)
                return v
            except pytz.exceptions.UnknownTimeZoneError:
                raise ValueError(f'無效的時區: {v}')
        return v


class ApiResponse(BaseModel):
    """標準API響應結構"""
    
    success: bool
    message: str
    data: Optional[dict] = None
    error_code: Optional[str] = None


class ErrorResponse(BaseModel):
    """錯誤響應結構"""
    
    success: bool = False
    message: str
    error_code: str
    details: Optional[dict] = None


# 更新前向引用
TokenResponse.model_rebuild()