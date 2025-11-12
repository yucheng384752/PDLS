"""Email notification system for PDLS application"""

import logging
import smtplib
import ssl
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional, Dict, Any, Union
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, Template
from dataclasses import dataclass
import asyncio
import aiofiles
import aiosmtplib

from .config import settings
from .logging import get_logger

logger = get_logger(__name__)


@dataclass
class EmailAttachment:
    """Email attachment data"""
    filename: str
    content: bytes
    content_type: str = "application/octet-stream"


@dataclass
class EmailAddress:
    """Email address with optional name"""
    email: str
    name: Optional[str] = None
    
    def __str__(self) -> str:
        if self.name:
            return f"{self.name} <{self.email}>"
        return self.email


class EmailTemplate:
    """Email template management"""
    
    def __init__(self, template_dir: Optional[Path] = None):
        self.template_dir = template_dir or Path(__file__).parent.parent / "templates" / "email"
        self.template_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render email template with context"""
        try:
            template = self.env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            logger.error(f"Failed to render email template '{template_name}': {e}")
            raise
    
    def render_string_template(self, template_string: str, context: Dict[str, Any]) -> str:
        """Render template from string"""
        try:
            template = Template(template_string)
            return template.render(**context)
        except Exception as e:
            logger.error(f"Failed to render string template: {e}")
            raise


class EmailService:
    """Async email service using aiosmtplib"""
    
    def __init__(self):
        self.template_manager = EmailTemplate()
        self.smtp_config = {
            'hostname': settings.SMTP_HOST,
            'port': settings.SMTP_PORT,
            'use_tls': settings.SMTP_USE_TLS,
            'username': settings.SMTP_USERNAME,
            'password': settings.SMTP_PASSWORD,
        }
    
    async def send_email(
        self,
        to_addresses: Union[EmailAddress, List[EmailAddress]],
        subject: str,
        html_content: Optional[str] = None,
        text_content: Optional[str] = None,
        from_address: Optional[EmailAddress] = None,
        cc_addresses: Optional[List[EmailAddress]] = None,
        bcc_addresses: Optional[List[EmailAddress]] = None,
        attachments: Optional[List[EmailAttachment]] = None,
        reply_to: Optional[EmailAddress] = None
    ) -> bool:
        """
        Send email with optional HTML/text content and attachments
        
        Args:
            to_addresses: Recipient email addresses
            subject: Email subject
            html_content: HTML email content
            text_content: Plain text email content
            from_address: Sender address (uses default if not provided)
            cc_addresses: CC recipients
            bcc_addresses: BCC recipients
            attachments: File attachments
            reply_to: Reply-to address
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Prepare recipient lists
            if isinstance(to_addresses, EmailAddress):
                to_addresses = [to_addresses]
            
            if not to_addresses:
                logger.error("No recipient addresses provided")
                return False
            
            # Use default sender if not provided
            if not from_address:
                from_address = EmailAddress(
                    email=settings.SMTP_FROM_EMAIL,
                    name=settings.SMTP_FROM_NAME
                )
            
            # Create message
            message = MIMEMultipart('alternative')
            message['Subject'] = subject
            message['From'] = str(from_address)
            message['To'] = ', '.join(str(addr) for addr in to_addresses)
            
            if cc_addresses:
                message['Cc'] = ', '.join(str(addr) for addr in cc_addresses)
            
            if reply_to:
                message['Reply-To'] = str(reply_to)
            
            # Add message ID and date
            message['Message-ID'] = aiosmtplib.email.utils.make_msgid()
            message['Date'] = aiosmtplib.email.utils.formatdate(localtime=True)
            
            # Add content
            if text_content:
                text_part = MIMEText(text_content, 'plain', 'utf-8')
                message.attach(text_part)
            
            if html_content:
                html_part = MIMEText(html_content, 'html', 'utf-8')
                message.attach(html_part)
            
            if not text_content and not html_content:
                logger.error("No email content provided")
                return False
            
            # Add attachments
            if attachments:
                for attachment in attachments:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.content)
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {attachment.filename}'
                    )
                    message.attach(part)
            
            # Collect all recipients
            all_recipients = [addr.email for addr in to_addresses]
            if cc_addresses:
                all_recipients.extend(addr.email for addr in cc_addresses)
            if bcc_addresses:
                all_recipients.extend(addr.email for addr in bcc_addresses)
            
            # Send email
            await aiosmtplib.send(
                message,
                recipients=all_recipients,
                sender=from_address.email,
                **self.smtp_config
            )
            
            logger.info(f"Email sent successfully to {len(all_recipients)} recipients: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email '{subject}': {e}")
            return False
    
    async def send_template_email(
        self,
        to_addresses: Union[EmailAddress, List[EmailAddress]],
        template_name: str,
        context: Dict[str, Any],
        subject: Optional[str] = None,
        from_address: Optional[EmailAddress] = None,
        **kwargs
    ) -> bool:
        """
        Send email using template
        
        Args:
            to_addresses: Recipient addresses
            template_name: Template file name (without .html/.txt extension)
            context: Template context variables
            subject: Email subject (will try to extract from template if not provided)
            from_address: Sender address
            **kwargs: Additional send_email parameters
            
        Returns:
            True if email sent successfully
        """
        try:
            # Try to load HTML and text templates
            html_content = None
            text_content = None
            
            try:
                html_content = self.template_manager.render_template(
                    f"{template_name}.html", context
                )
            except:
                pass
            
            try:
                text_content = self.template_manager.render_template(
                    f"{template_name}.txt", context
                )
            except:
                pass
            
            if not html_content and not text_content:
                logger.error(f"No templates found for '{template_name}'")
                return False
            
            # Extract subject from template if not provided
            if not subject:
                subject = context.get('subject', f'Notification from {settings.PROJECT_NAME}')
            
            return await self.send_email(
                to_addresses=to_addresses,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                from_address=from_address,
                **kwargs
            )
            
        except Exception as e:
            logger.error(f"Failed to send template email '{template_name}': {e}")
            return False


# Global email service instance
email_service = EmailService()


# Pre-defined notification types
class NotificationTemplates:
    """Pre-defined email notification templates"""
    
    @staticmethod
    async def send_welcome_email(user_email: str, user_name: str, login_url: str) -> bool:
        """Send welcome email to new user"""
        context = {
            'user_name': user_name,
            'login_url': login_url,
            'app_name': settings.PROJECT_NAME,
            'support_email': settings.SMTP_FROM_EMAIL,
        }
        
        return await email_service.send_template_email(
            to_addresses=EmailAddress(user_email, user_name),
            template_name='welcome',
            subject=f'歡迎加入 {settings.PROJECT_NAME}！',
            context=context
        )
    
    @staticmethod
    async def send_password_reset_email(
        user_email: str, 
        user_name: str, 
        reset_token: str,
        reset_url: str
    ) -> bool:
        """Send password reset email"""
        context = {
            'user_name': user_name,
            'reset_token': reset_token,
            'reset_url': reset_url,
            'app_name': settings.PROJECT_NAME,
            'expiry_hours': 24,
        }
        
        return await email_service.send_template_email(
            to_addresses=EmailAddress(user_email, user_name),
            template_name='password_reset',
            subject=f'{settings.PROJECT_NAME} 密碼重設請求',
            context=context
        )
    
    @staticmethod
    async def send_project_invitation_email(
        user_email: str,
        user_name: str,
        project_name: str,
        inviter_name: str,
        invitation_url: str
    ) -> bool:
        """Send project invitation email"""
        context = {
            'user_name': user_name,
            'project_name': project_name,
            'inviter_name': inviter_name,
            'invitation_url': invitation_url,
            'app_name': settings.PROJECT_NAME,
        }
        
        return await email_service.send_template_email(
            to_addresses=EmailAddress(user_email, user_name),
            template_name='project_invitation',
            subject=f'邀請您加入專案: {project_name}',
            context=context
        )
    
    @staticmethod
    async def send_log_comment_notification(
        user_email: str,
        user_name: str,
        log_title: str,
        commenter_name: str,
        comment_content: str,
        log_url: str
    ) -> bool:
        """Send notification for new comment on development log"""
        context = {
            'user_name': user_name,
            'log_title': log_title,
            'commenter_name': commenter_name,
            'comment_content': comment_content[:200] + '...' if len(comment_content) > 200 else comment_content,
            'log_url': log_url,
            'app_name': settings.PROJECT_NAME,
        }
        
        return await email_service.send_template_email(
            to_addresses=EmailAddress(user_email, user_name),
            template_name='log_comment',
            subject=f'新留言: {log_title}',
            context=context
        )
    
    @staticmethod
    async def send_weekly_digest_email(
        user_email: str,
        user_name: str,
        digest_data: Dict[str, Any]
    ) -> bool:
        """Send weekly activity digest email"""
        context = {
            'user_name': user_name,
            'app_name': settings.PROJECT_NAME,
            **digest_data
        }
        
        return await email_service.send_template_email(
            to_addresses=EmailAddress(user_email, user_name),
            template_name='weekly_digest',
            subject=f'{settings.PROJECT_NAME} 週報',
            context=context
        )


# Email queue for background processing
class EmailQueue:
    """Simple email queue for background processing"""
    
    def __init__(self):
        self.queue = asyncio.Queue()
        self.worker_task = None
    
    async def start_worker(self):
        """Start background email worker"""
        if self.worker_task and not self.worker_task.done():
            return
        
        self.worker_task = asyncio.create_task(self._process_queue())
        logger.info("Email queue worker started")
    
    async def stop_worker(self):
        """Stop background email worker"""
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
        logger.info("Email queue worker stopped")
    
    async def add_email(self, email_func, *args, **kwargs):
        """Add email to queue for background processing"""
        await self.queue.put((email_func, args, kwargs))
        logger.debug(f"Email added to queue: {email_func.__name__}")
    
    async def _process_queue(self):
        """Process emails in background"""
        while True:
            try:
                email_func, args, kwargs = await self.queue.get()
                
                try:
                    success = await email_func(*args, **kwargs)
                    if success:
                        logger.debug(f"Email processed successfully: {email_func.__name__}")
                    else:
                        logger.error(f"Failed to process email: {email_func.__name__}")
                except Exception as e:
                    logger.error(f"Error processing email {email_func.__name__}: {e}")
                
                self.queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Email queue worker error: {e}")
                await asyncio.sleep(5)  # Wait before retrying


# Global email queue instance
email_queue = EmailQueue()


# Utility functions
async def send_notification_email(
    notification_type: str,
    recipient_email: str,
    **context
) -> bool:
    """
    Send notification email by type
    
    Args:
        notification_type: Type of notification (welcome, password_reset, etc.)
        recipient_email: Recipient email address
        **context: Template context variables
        
    Returns:
        True if email queued successfully
    """
    try:
        # Map notification types to template functions
        notification_handlers = {
            'welcome': NotificationTemplates.send_welcome_email,
            'password_reset': NotificationTemplates.send_password_reset_email,
            'project_invitation': NotificationTemplates.send_project_invitation_email,
            'log_comment': NotificationTemplates.send_log_comment_notification,
            'weekly_digest': NotificationTemplates.send_weekly_digest_email,
        }
        
        handler = notification_handlers.get(notification_type)
        if not handler:
            logger.error(f"Unknown notification type: {notification_type}")
            return False
        
        # Add to queue for background processing
        await email_queue.add_email(handler, recipient_email, **context)
        return True
        
    except Exception as e:
        logger.error(f"Failed to queue notification email: {e}")
        return False


async def init_email_service():
    """Initialize email service"""
    try:
        await email_queue.start_worker()
        logger.info("Email service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize email service: {e}")
        raise


async def shutdown_email_service():
    """Shutdown email service"""
    try:
        await email_queue.stop_worker()
        logger.info("Email service shutdown successfully")
    except Exception as e:
        logger.error(f"Failed to shutdown email service: {e}")


# Health check
async def check_email_service_health() -> Dict[str, Any]:
    """Check email service health"""
    try:
        # Try to connect to SMTP server
        smtp_config = {
            'hostname': settings.SMTP_HOST,
            'port': settings.SMTP_PORT,
            'use_tls': settings.SMTP_USE_TLS,
        }
        
        async with aiosmtplib.SMTP(**smtp_config) as smtp:
            if settings.SMTP_USERNAME:
                await smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        
        return {
            'status': 'healthy',
            'smtp_host': settings.SMTP_HOST,
            'smtp_port': settings.SMTP_PORT,
            'queue_size': email_queue.queue.qsize(),
            'worker_running': email_queue.worker_task and not email_queue.worker_task.done()
        }
        
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
            'smtp_host': settings.SMTP_HOST,
            'smtp_port': settings.SMTP_PORT
        }