"""Authentication API endpoints for PDLS"""

from datetime import datetime
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.email_simple import get_email_service
from src.services.auth import (
    AuthService,
    UserAlreadyExistsError,
    InvalidCredentialsError,
    AccountLockedError
)
from src.schemas.auth import (
    UserRegistrationRequest,
    UserRegistrationResponse,
    UserLoginRequest,
    TokenResponse,
    UserProfile,
    PasswordResetRequest,
    PasswordResetConfirm,
    EmailVerificationRequest,
    PasswordChangeRequest,
    UserUpdateRequest,
    ApiResponse,
    ErrorResponse
)
from src.models.user import User
import logging

logger = logging.getLogger(__name__)

# 創建路由器
router = APIRouter(prefix="/auth", tags=["認證"])

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


async def get_auth_service(
    email_service = Depends(get_email_service)
) -> AuthService:
    """獲取認證服務實例"""
    return AuthService(email_service)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
) -> User:
    """
    獲取當前認證用戶
    
    Args:
        credentials: HTTP Bearer 憑證
        db: 數據庫會話
        auth_service: 認證服務
        
    Returns:
        當前用戶實例
        
    Raises:
        HTTPException: 401 如果認證失敗
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要認證",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    try:
        # 驗證令牌
        payload = auth_service.verify_token(credentials.credentials, "access")
        user_id = int(payload["sub"])
        
        # 獲取用戶
        user = await db.get(User, user_id)
        if not user or not user.is_active_user():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用戶不存在或未激活"
            )
        
        return user
        
    except Exception as e:
        logger.warning(f"認證失敗: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無效的認證令牌",
            headers={"WWW-Authenticate": "Bearer"}
        )


def get_client_ip(request: Request) -> str:
    """獲取客戶端IP地址"""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    return request.client.host if request.client else "unknown"


@router.post(
    "/register",
    response_model=UserRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="用戶註冊",
    description="註冊新用戶帳戶，會發送郵箱驗證郵件"
)
async def register_user(
    registration_data: UserRegistrationRequest,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    註冊新用戶
    
    - **username**: 用戶名（3-50字符，唯一）
    - **email**: 電子郵件地址（唯一）
    - **password**: 密碼（至少8字符，包含字母和數字）
    - **full_name**: 用戶全名（可選）
    - **timezone**: 時區（默認UTC）
    - **language**: 語言（默認zh-tw）
    
    註冊成功後會發送郵箱驗證郵件到用戶郵箱。
    """
    try:
        user = await auth_service.register_user(db, registration_data)
        
        return UserRegistrationResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            status=user.status,
            is_email_verified=user.is_email_verified,
            created_at=user.created_at
        )
        
    except UserAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"用戶註冊失敗: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="註冊失敗，請稍後重試"
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="用戶登入",
    description="用戶登入並獲取認證令牌"
)
async def login_user(
    login_data: UserLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    用戶登入
    
    - **username_or_email**: 用戶名或電子郵件地址
    - **password**: 密碼
    - **remember_me**: 記住我（延長令牌有效期）
    
    登入成功後返回訪問令牌和刷新令牌。
    """
    try:
        client_ip = get_client_ip(request)
        user, tokens = await auth_service.authenticate_user(db, login_data, client_ip)
        
        # 構建用戶資料
        user_profile = UserProfile(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            status=user.status,
            is_email_verified=user.is_email_verified,
            avatar_url=user.avatar_url,
            bio=user.bio,
            timezone=user.timezone,
            language=user.language,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
        
        return TokenResponse(
            **tokens,
            user=user_profile
        )
        
    except (InvalidCredentialsError, AccountLockedError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"用戶登入失敗: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登入失敗，請稍後重試"
        )


@router.post(
    "/verify-email",
    response_model=ApiResponse,
    summary="驗證電子郵件",
    description="使用令牌驗證用戶電子郵件地址"
)
async def verify_email(
    verification_data: EmailVerificationRequest,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    驗證電子郵件
    
    - **token**: 從郵件中獲取的驗證令牌
    
    驗證成功後用戶帳戶將被激活。
    """
    try:
        user = await auth_service.verify_email(db, verification_data.token)
        
        return ApiResponse(
            success=True,
            message=f"郵箱 {user.email} 驗證成功，帳戶已激活"
        )
        
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"郵箱驗證失敗: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="驗證失敗，請稍後重試"
        )


@router.post(
    "/forgot-password",
    response_model=ApiResponse,
    summary="忘記密碼",
    description="發送密碼重設郵件"
)
async def forgot_password(
    reset_request: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    忘記密碼
    
    - **email**: 註冊的電子郵件地址
    
    如果郵箱存在，將發送密碼重設郵件。
    """
    try:
        success = await auth_service.request_password_reset(db, reset_request)
        
        return ApiResponse(
            success=True,
            message="如果該郵箱已註冊，您將收到密碼重設郵件"
        )
        
    except Exception as e:
        logger.error(f"密碼重設請求失敗: {str(e)}")
        # 為了安全考慮，始終返回成功消息
        return ApiResponse(
            success=True,
            message="如果該郵箱已註冊，您將收到密碼重設郵件"
        )


@router.post(
    "/reset-password",
    response_model=ApiResponse,
    summary="重設密碼",
    description="使用令牌重設用戶密碼"
)
async def reset_password(
    reset_confirm: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    重設密碼
    
    - **token**: 從郵件中獲取的重設令牌
    - **new_password**: 新密碼（至少8字符，包含字母和數字）
    
    重設成功後用戶需要使用新密碼登入。
    """
    try:
        user = await auth_service.confirm_password_reset(db, reset_confirm)
        
        return ApiResponse(
            success=True,
            message="密碼重設成功，請使用新密碼登入"
        )
        
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"密碼重設失敗: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="重設失敗，請稍後重試"
        )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="刷新令牌",
    description="使用刷新令牌獲取新的訪問令牌"
)
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    刷新令牌
    
    - **refresh_token**: 刷新令牌
    
    返回新的訪問令牌和用戶信息。
    """
    try:
        tokens = await auth_service.refresh_access_token(db, refresh_token)
        
        # 獲取用戶信息
        payload = auth_service.verify_token(tokens["access_token"], "access")
        user_id = int(payload["sub"])
        user = await db.get(User, user_id)
        
        user_profile = UserProfile(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            status=user.status,
            is_email_verified=user.is_email_verified,
            avatar_url=user.avatar_url,
            bio=user.bio,
            timezone=user.timezone,
            language=user.language,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
        
        return TokenResponse(
            **tokens,
            user=user_profile
        )
        
    except Exception as e:
        logger.warning(f"令牌刷新失敗: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無效的刷新令牌"
        )


@router.get(
    "/me",
    response_model=UserProfile,
    summary="獲取當前用戶信息",
    description="獲取當前認證用戶的個人資料"
)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    獲取當前用戶信息
    
    需要有效的認證令牌。
    """
    return UserProfile(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        status=current_user.status,
        is_email_verified=current_user.is_email_verified,
        avatar_url=current_user.avatar_url,
        bio=current_user.bio,
        timezone=current_user.timezone,
        language=current_user.language,
        last_login_at=current_user.last_login_at,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )


@router.put(
    "/me",
    response_model=UserProfile,
    summary="更新用戶資料",
    description="更新當前認證用戶的個人資料"
)
async def update_current_user(
    update_data: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    更新用戶資料
    
    - **full_name**: 用戶全名
    - **bio**: 用戶簡介
    - **timezone**: 時區
    - **language**: 語言偏好
    
    需要有效的認證令牌。
    """
    try:
        updated_user = await auth_service.update_user_profile(
            db, current_user, update_data
        )
        
        return UserProfile(
            id=updated_user.id,
            username=updated_user.username,
            email=updated_user.email,
            full_name=updated_user.full_name,
            role=updated_user.role,
            status=updated_user.status,
            is_email_verified=updated_user.is_email_verified,
            avatar_url=updated_user.avatar_url,
            bio=updated_user.bio,
            timezone=updated_user.timezone,
            language=updated_user.language,
            last_login_at=updated_user.last_login_at,
            created_at=updated_user.created_at,
            updated_at=updated_user.updated_at
        )
        
    except Exception as e:
        logger.error(f"用戶資料更新失敗: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新失敗，請稍後重試"
        )


@router.post(
    "/change-password",
    response_model=ApiResponse,
    summary="更改密碼",
    description="更改當前認證用戶的密碼"
)
async def change_password(
    password_change: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    更改密碼
    
    - **current_password**: 當前密碼
    - **new_password**: 新密碼（至少8字符，包含字母和數字）
    
    需要有效的認證令牌。
    """
    try:
        await auth_service.change_password(db, current_user, password_change)
        
        return ApiResponse(
            success=True,
            message="密碼更改成功"
        )
        
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"密碼更改失敗: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更改失敗，請稍後重試"
        )