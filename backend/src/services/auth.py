"""Authentication service for user management in PDLS"""

from datetime import datetime, timedelta
from typing import Optional, Union, Tuple
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from jose import JWTError, jwt
import secrets
import logging

from src.models.user import User, UserRole, UserStatus
from src.schemas.auth import (
    UserRegistrationRequest,
    UserLoginRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    PasswordChangeRequest,
    UserUpdateRequest
)
from src.core.config import settings
from src.core.email_simple import EmailService

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """認證相關錯誤"""
    pass


class UserAlreadyExistsError(Exception):
    """用戶已存在錯誤"""
    pass


class InvalidCredentialsError(Exception):
    """無效認證信息錯誤"""
    pass


class AccountLockedError(Exception):
    """帳戶被鎖定錯誤"""
    pass


class AuthService:
    """認證服務類"""
    
    def __init__(self, email_service: EmailService):
        self.email_service = email_service
    
    async def register_user(
        self,
        db: AsyncSession,
        registration_data: UserRegistrationRequest,
        send_verification_email: bool = True
    ) -> User:
        """
        註冊新用戶
        
        Args:
            db: 數據庫會話
            registration_data: 註冊數據
            send_verification_email: 是否發送驗證郵件
            
        Returns:
            新創建的用戶實例
            
        Raises:
            UserAlreadyExistsError: 用戶已存在
        """
        # 檢查用戶名是否已存在
        existing_user = await self._get_user_by_username_or_email(
            db, registration_data.username, registration_data.email
        )
        
        if existing_user:
            if existing_user.username == registration_data.username:
                raise UserAlreadyExistsError("用戶名已被使用")
            if existing_user.email == registration_data.email:
                raise UserAlreadyExistsError("電子郵件地址已被註冊")
        
        # 創建新用戶
        user = User.create_user(
            username=registration_data.username,
            email=registration_data.email,
            password=registration_data.password,
            full_name=registration_data.full_name,
            role=UserRole.DEVELOPER,
            send_verification=send_verification_email
        )
        
        # 設置額外屬性
        user.timezone = registration_data.timezone
        user.language = registration_data.language
        
        # 保存到數據庫
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        # 發送驗證郵件
        if send_verification_email and user.email_verification_token:
            try:
                await self._send_verification_email(user)
                logger.info(f"驗證郵件已發送至 {user.email}")
            except Exception as e:
                logger.error(f"發送驗證郵件失敗: {str(e)}")
                # 不拋出異常，因為用戶已經註冊成功
        
        return user
    
    async def authenticate_user(
        self,
        db: AsyncSession,
        login_data: UserLoginRequest,
        ip_address: str
    ) -> Tuple[User, dict]:
        """
        認證用戶登入
        
        Args:
            db: 數據庫會話
            login_data: 登入數據
            ip_address: 客戶端IP地址
            
        Returns:
            元組 (用戶實例, 令牌信息)
            
        Raises:
            InvalidCredentialsError: 無效認證信息
            AccountLockedError: 帳戶被鎖定
        """
        # 獲取用戶
        user = await self._get_user_by_username_or_email(
            db, login_data.username_or_email
        )
        
        if not user:
            raise InvalidCredentialsError("用戶名或密碼錯誤")
        
        # 檢查帳戶狀態
        if user.is_account_locked():
            raise AccountLockedError(f"帳戶已被鎖定，請於 {user.locked_until} 後重試")
        
        if not user.is_active_user():
            raise InvalidCredentialsError("帳戶未激活或已被停用")
        
        # 驗證密碼
        if not user.verify_password(login_data.password):
            # 增加失敗登入次數
            user.increment_failed_login()
            await db.commit()
            
            remaining_attempts = 5 - user.failed_login_attempts
            if remaining_attempts <= 0:
                raise AccountLockedError("帳戶已被鎖定，請稍後重試")
            
            raise InvalidCredentialsError(f"用戶名或密碼錯誤，剩餘嘗試次數: {remaining_attempts}")
        
        # 登入成功，記錄登入信息
        user.record_successful_login(ip_address)
        await db.commit()
        
        # 生成令牌
        tokens = self._generate_tokens(user, login_data.remember_me)
        
        return user, tokens
    
    async def verify_email(self, db: AsyncSession, token: str) -> User:
        """
        驗證電子郵件
        
        Args:
            db: 數據庫會話
            token: 驗證令牌
            
        Returns:
            用戶實例
            
        Raises:
            InvalidCredentialsError: 無效或過期的令牌
        """
        # 查找具有該驗證令牌的用戶
        query = select(User).where(
            and_(
                User.email_verification_token.isnot(None),
                User.email_verification_expires > datetime.utcnow(),
                User.is_deleted == False
            )
        )
        
        result = await db.execute(query)
        users = result.scalars().all()
        
        # 驗證令牌
        for user in users:
            if user.verify_email_token(token):
                if user.confirm_email(token):
                    await db.commit()
                    await db.refresh(user)
                    logger.info(f"用戶 {user.username} 郵箱驗證成功")
                    return user
        
        raise InvalidCredentialsError("無效或過期的驗證令牌")
    
    async def request_password_reset(
        self,
        db: AsyncSession,
        reset_request: PasswordResetRequest
    ) -> bool:
        """
        請求密碼重設
        
        Args:
            db: 數據庫會話
            reset_request: 重設請求數據
            
        Returns:
            是否成功發送重設郵件
        """
        user = await self._get_user_by_email(db, reset_request.email)
        
        if not user or not user.is_active_user():
            # 為了安全考慮，不透露用戶是否存在
            logger.warning(f"密碼重設請求 - 用戶不存在或未激活: {reset_request.email}")
            return True  # 仍返回成功避免用戶枚舉
        
        # 生成重設令牌
        token = user.generate_password_reset_token()
        await db.commit()
        
        # 發送重設郵件
        try:
            await self._send_password_reset_email(user, token)
            logger.info(f"密碼重設郵件已發送至 {user.email}")
            return True
        except Exception as e:
            logger.error(f"發送密碼重設郵件失敗: {str(e)}")
            return False
    
    async def confirm_password_reset(
        self,
        db: AsyncSession,
        reset_confirm: PasswordResetConfirm
    ) -> User:
        """
        確認密碼重設
        
        Args:
            db: 數據庫會話
            reset_confirm: 重設確認數據
            
        Returns:
            用戶實例
            
        Raises:
            InvalidCredentialsError: 無效或過期的令牌
        """
        # 查找具有該重設令牌的用戶
        query = select(User).where(
            and_(
                User.password_reset_token.isnot(None),
                User.password_reset_expires > datetime.utcnow(),
                User.is_deleted == False
            )
        )
        
        result = await db.execute(query)
        users = result.scalars().all()
        
        # 驗證令牌並重設密碼
        for user in users:
            if user.verify_password_reset_token(reset_confirm.token):
                if user.reset_password(reset_confirm.token, reset_confirm.new_password):
                    await db.commit()
                    await db.refresh(user)
                    logger.info(f"用戶 {user.username} 密碼重設成功")
                    return user
        
        raise InvalidCredentialsError("無效或過期的重設令牌")
    
    async def change_password(
        self,
        db: AsyncSession,
        user: User,
        password_change: PasswordChangeRequest
    ) -> User:
        """
        更改用戶密碼
        
        Args:
            db: 數據庫會話
            user: 用戶實例
            password_change: 密碼更改數據
            
        Returns:
            更新後的用戶實例
            
        Raises:
            InvalidCredentialsError: 當前密碼錯誤
        """
        # 驗證當前密碼
        if not user.verify_password(password_change.current_password):
            raise InvalidCredentialsError("當前密碼錯誤")
        
        # 設置新密碼
        user.set_password(password_change.new_password)
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"用戶 {user.username} 密碼更改成功")
        return user
    
    async def update_user_profile(
        self,
        db: AsyncSession,
        user: User,
        update_data: UserUpdateRequest
    ) -> User:
        """
        更新用戶資料
        
        Args:
            db: 數據庫會話
            user: 用戶實例
            update_data: 更新數據
            
        Returns:
            更新後的用戶實例
        """
        # 更新允許的字段
        update_dict = update_data.dict(exclude_unset=True)
        user.update_profile(**update_dict)
        
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"用戶 {user.username} 資料更新成功")
        return user
    
    def _generate_tokens(self, user: User, remember_me: bool = False) -> dict:
        """
        生成JWT令牌
        
        Args:
            user: 用戶實例
            remember_me: 是否延長有效期
            
        Returns:
            包含訪問令牌和刷新令牌的字典
        """
        # 設置過期時間
        access_expire = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_expire = timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS * (7 if remember_me else 1)
        )
        
        # 訪問令牌載荷
        access_payload = {
            "sub": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
            "exp": datetime.utcnow() + access_expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        # 刷新令牌載荷
        refresh_payload = {
            "sub": str(user.id),
            "exp": datetime.utcnow() + refresh_expire,
            "iat": datetime.utcnow(),
            "type": "refresh",
            "jti": secrets.token_urlsafe(16)  # JWT ID for refresh token
        }
        
        # 生成令牌
        access_token = jwt.encode(
            access_payload, 
            settings.JWT_SECRET_KEY, 
            algorithm=settings.JWT_ALGORITHM
        )
        
        refresh_token = jwt.encode(
            refresh_payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": int(access_expire.total_seconds())
        }
    
    def verify_token(self, token: str, token_type: str = "access") -> dict:
        """
        驗證JWT令牌
        
        Args:
            token: JWT令牌
            token_type: 令牌類型 (access/refresh)
            
        Returns:
            令牌載荷
            
        Raises:
            JWTError: 令牌無效或過期
        """
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            # 檢查令牌類型
            if payload.get("type") != token_type:
                raise JWTError("令牌類型錯誤")
            
            return payload
            
        except JWTError as e:
            logger.warning(f"令牌驗證失敗: {str(e)}")
            raise
    
    async def refresh_access_token(
        self,
        db: AsyncSession,
        refresh_token: str
    ) -> dict:
        """
        使用刷新令牌獲取新的訪問令牌
        
        Args:
            db: 數據庫會話
            refresh_token: 刷新令牌
            
        Returns:
            新的令牌信息
            
        Raises:
            JWTError: 無效的刷新令牌
        """
        try:
            # 驗證刷新令牌
            payload = self.verify_token(refresh_token, "refresh")
            user_id = int(payload["sub"])
            
            # 獲取用戶
            user = await db.get(User, user_id)
            if not user or not user.is_active_user():
                raise JWTError("用戶不存在或未激活")
            
            # 生成新的訪問令牌
            tokens = self._generate_tokens(user)
            return tokens
            
        except (JWTError, ValueError) as e:
            logger.warning(f"刷新令牌失敗: {str(e)}")
            raise JWTError("無效的刷新令牌")
    
    # Private helper methods
    async def _get_user_by_username_or_email(
        self,
        db: AsyncSession,
        username_or_email: str,
        email: Optional[str] = None
    ) -> Optional[User]:
        """根據用戶名或郵箱查找用戶"""
        if email:
            # 同時檢查用戶名和郵箱
            query = select(User).where(
                and_(
                    (User.username == username_or_email) | (User.email == email),
                    User.is_deleted == False
                )
            )
        else:
            # 只檢查用戶名或郵箱
            query = select(User).where(
                and_(
                    (User.username == username_or_email) | (User.email == username_or_email),
                    User.is_deleted == False
                )
            )
        
        result = await db.execute(query)
        return result.scalars().first()
    
    async def _get_user_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """根據郵箱查找用戶"""
        query = select(User).where(
            and_(
                User.email == email,
                User.is_deleted == False
            )
        )
        result = await db.execute(query)
        return result.scalars().first()
    
    async def _send_verification_email(self, user: User) -> None:
        """發送郵箱驗證郵件"""
        # 生成驗證URL（這裡需要根據實際前端路由調整）
        verification_url = f"http://localhost:3000/verify-email?token={user.email_verification_token}"
        
        await self.email_service.send_welcome_email(
            user.email,
            user.full_name or user.username,
            verification_url
        )
    
    async def _send_password_reset_email(self, user: User, token: str) -> None:
        """發送密碼重設郵件"""
        # 生成重設URL（這裡需要根據實際前端路由調整）
        reset_url = f"http://localhost:3000/reset-password?token={token}"
        
        await self.email_service.send_password_reset_email(
            user.email,
            user.full_name or user.username,
            reset_url
        )