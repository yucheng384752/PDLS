"""
Notification service for PDLS

Handles various types of notifications:
- Email notifications
- In-app notifications
- Project-related notifications
- System notifications
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..models.user import User
from ..models.project import Project, ProjectInvitation, ProjectMember
from ..core.config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for handling application notifications"""
    
    @staticmethod
    async def send_project_created_notification(
        project: Project,
        creator: User
    ) -> bool:
        """
        Send notification when a project is created
        
        Args:
            project: Created project
            creator: User who created the project
            
        Returns:
            True if notification sent successfully
        """
        try:
            logger.info(f"Project created: {project.name} by {creator.username}")
            
            # In a real implementation, this would:
            # 1. Send email to project owner (if different from creator)
            # 2. Create in-app notification
            # 3. Send to notification queue for processing
            
            # For now, just log the notification
            notification_data = {
                "type": "project_created",
                "project_id": project.id,
                "project_name": project.name,
                "creator_id": creator.id,
                "creator_name": creator.username,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Notification data: {notification_data}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send project created notification: {str(e)}")
            return False
    
    @staticmethod
    async def send_project_deleted_notification(
        project: Project,
        deleted_by: User
    ) -> bool:
        """
        Send notification when a project is deleted
        
        Args:
            project: Deleted project
            deleted_by: User who deleted the project
            
        Returns:
            True if notification sent successfully
        """
        try:
            logger.info(f"Project deleted: {project.name} by {deleted_by.username}")
            
            # Notify all project members about deletion
            notification_data = {
                "type": "project_deleted",
                "project_id": project.id,
                "project_name": project.name,
                "deleted_by_id": deleted_by.id,
                "deleted_by_name": deleted_by.username,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Notification data: {notification_data}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send project deleted notification: {str(e)}")
            return False
    
    @staticmethod
    async def send_project_member_added_notification(
        project: Project,
        new_member: User,
        added_by: User
    ) -> bool:
        """
        Send notification when a member is added to project
        
        Args:
            project: Project where member was added
            new_member: User who was added
            added_by: User who added the member
            
        Returns:
            True if notification sent successfully
        """
        try:
            logger.info(f"Member added to project {project.name}: {new_member.username} by {added_by.username}")
            
            # Notify the new member and project owner
            notification_data = {
                "type": "member_added",
                "project_id": project.id,
                "project_name": project.name,
                "new_member_id": new_member.id,
                "new_member_name": new_member.username,
                "added_by_id": added_by.id,
                "added_by_name": added_by.username,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Notification data: {notification_data}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send member added notification: {str(e)}")
            return False
    
    @staticmethod
    async def send_project_member_removed_notification(
        project: Project,
        removed_member: User,
        removed_by: User
    ) -> bool:
        """
        Send notification when a member is removed from project
        
        Args:
            project: Project where member was removed
            removed_member: User who was removed
            removed_by: User who removed the member
            
        Returns:
            True if notification sent successfully
        """
        try:
            logger.info(f"Member removed from project {project.name}: {removed_member.username} by {removed_by.username}")
            
            notification_data = {
                "type": "member_removed",
                "project_id": project.id,
                "project_name": project.name,
                "removed_member_id": removed_member.id,
                "removed_member_name": removed_member.username,
                "removed_by_id": removed_by.id,
                "removed_by_name": removed_by.username,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Notification data: {notification_data}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send member removed notification: {str(e)}")
            return False
    
    @staticmethod
    async def send_project_invitation_notification(
        invitation: ProjectInvitation,
        project: Project,
        inviter: User
    ) -> bool:
        """
        Send notification for project invitation
        
        Args:
            invitation: Project invitation
            project: Project for invitation
            inviter: User who sent the invitation
            
        Returns:
            True if notification sent successfully
        """
        try:
            logger.info(f"Project invitation sent for {project.name} by {inviter.username}")
            
            # Send email to invited user
            notification_data = {
                "type": "project_invitation",
                "invitation_id": invitation.id,
                "project_id": project.id,
                "project_name": project.name,
                "inviter_id": inviter.id,
                "inviter_name": inviter.username,
                "invited_email": invitation.invited_email,
                "invitation_token": invitation.token,
                "expires_at": invitation.expires_at.isoformat() if invitation.expires_at else None,
                "message": invitation.message,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Invitation notification data: {notification_data}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send invitation notification: {str(e)}")
            return False
    
    @staticmethod
    async def send_invitation_response_notification(
        invitation: ProjectInvitation,
        responder: User
    ) -> bool:
        """
        Send notification when invitation is responded to
        
        Args:
            invitation: Project invitation that was responded to
            responder: User who responded to invitation
            
        Returns:
            True if notification sent successfully
        """
        try:
            logger.info(f"Invitation response: {invitation.status} by {responder.username}")
            
            notification_data = {
                "type": "invitation_response",
                "invitation_id": invitation.id,
                "project_id": invitation.project_id,
                "responder_id": responder.id,
                "responder_name": responder.username,
                "response": invitation.status.value,
                "responded_at": invitation.responded_at.isoformat() if invitation.responded_at else None,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Invitation response notification data: {notification_data}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send invitation response notification: {str(e)}")
            return False
    
    @staticmethod
    async def send_invitation_cancelled_notification(
        invitation: ProjectInvitation,
        cancelled_by: User
    ) -> bool:
        """
        Send notification when invitation is cancelled
        
        Args:
            invitation: Cancelled invitation
            cancelled_by: User who cancelled the invitation
            
        Returns:
            True if notification sent successfully
        """
        try:
            logger.info(f"Invitation cancelled by {cancelled_by.username}")
            
            notification_data = {
                "type": "invitation_cancelled",
                "invitation_id": invitation.id,
                "project_id": invitation.project_id,
                "cancelled_by_id": cancelled_by.id,
                "cancelled_by_name": cancelled_by.username,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Invitation cancelled notification data: {notification_data}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send invitation cancelled notification: {str(e)}")
            return False
    
    @staticmethod
    async def send_email_notification(
        to_email: str,
        subject: str,
        template: str,
        context: Dict[str, Any]
    ) -> bool:
        """
        Send email notification
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            template: Email template name
            context: Template context variables
            
        Returns:
            True if email sent successfully
        """
        try:
            logger.info(f"Sending email to {to_email}: {subject}")
            
            # In a real implementation, this would:
            # 1. Load email template
            # 2. Render template with context
            # 3. Send via SMTP or email service (SendGrid, AWS SES, etc.)
            
            email_data = {
                "to": to_email,
                "subject": subject,
                "template": template,
                "context": context,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Email data: {email_data}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {str(e)}")
            return False
    
    @staticmethod
    async def create_in_app_notification(
        user_id: int,
        title: str,
        message: str,
        notification_type: str = "info",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Create in-app notification for user
        
        Args:
            user_id: Target user ID
            title: Notification title
            message: Notification message
            notification_type: Type of notification (info, warning, error, success)
            metadata: Additional metadata
            
        Returns:
            True if notification created successfully
        """
        try:
            logger.info(f"Creating in-app notification for user {user_id}: {title}")
            
            # In a real implementation, this would:
            # 1. Create notification record in database
            # 2. Send to WebSocket connections for real-time updates
            # 3. Update notification counters
            
            notification_data = {
                "user_id": user_id,
                "title": title,
                "message": message,
                "type": notification_type,
                "metadata": metadata or {},
                "created_at": datetime.utcnow().isoformat(),
                "read": False
            }
            
            logger.info(f"In-app notification data: {notification_data}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create in-app notification: {str(e)}")
            return False
    
    @staticmethod
    async def send_bulk_notification(
        user_ids: List[int],
        title: str,
        message: str,
        notification_type: str = "info",
        email_notification: bool = False
    ) -> bool:
        """
        Send notification to multiple users
        
        Args:
            user_ids: List of user IDs
            title: Notification title
            message: Notification message
            notification_type: Type of notification
            email_notification: Whether to send email as well
            
        Returns:
            True if notifications sent successfully
        """
        try:
            logger.info(f"Sending bulk notification to {len(user_ids)} users: {title}")
            
            # In a real implementation, this would:
            # 1. Queue notifications for batch processing
            # 2. Send in-app notifications to all users
            # 3. Optionally send email notifications
            
            for user_id in user_ids:
                await NotificationService.create_in_app_notification(
                    user_id=user_id,
                    title=title,
                    message=message,
                    notification_type=notification_type
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send bulk notification: {str(e)}")
            return False