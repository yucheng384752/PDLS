"""Simplified email service for PDLS authentication"""

import logging
from typing import Optional

from .config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """簡化的郵件服務（用於演示，生產環境需要完整實作）"""
    
    def __init__(self):
        self.enabled = settings.ENABLE_EMAIL_NOTIFICATIONS
    
    async def send_welcome_email(
        self,
        email: str,
        name: str,
        verification_url: str
    ) -> bool:
        """
        發送歡迎郵件和郵箱驗證
        
        Args:
            email: 收件人郵箱
            name: 收件人姓名
            verification_url: 驗證連結
            
        Returns:
            是否發送成功
        """
        if not self.enabled:
            logger.info(f"郵件功能已禁用 - 跳過發送歡迎郵件至 {email}")
            logger.info(f"驗證連結: {verification_url}")
            return True
        
        # TODO: 實作實際的郵件發送邏輯
        logger.info(f"模擬發送歡迎郵件至 {email}")
        logger.info(f"收件人: {name}")
        logger.info(f"驗證連結: {verification_url}")
        
        return True
    
    async def send_password_reset_email(
        self,
        email: str,
        name: str,
        reset_url: str
    ) -> bool:
        """
        發送密碼重設郵件
        
        Args:
            email: 收件人郵箱
            name: 收件人姓名
            reset_url: 重設連結
            
        Returns:
            是否發送成功
        """
        if not self.enabled:
            logger.info(f"郵件功能已禁用 - 跳過發送密碼重設郵件至 {email}")
            logger.info(f"重設連結: {reset_url}")
            return True
        
        # TODO: 實作實際的郵件發送邏輯
        logger.info(f"模擬發送密碼重設郵件至 {email}")
        logger.info(f"收件人: {name}")
        logger.info(f"重設連結: {reset_url}")
        
        return True


def get_email_service() -> EmailService:
    """獲取郵件服務實例"""
    return EmailService()