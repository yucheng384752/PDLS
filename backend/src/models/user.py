"""User model for authentication and user management in PDLS"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum as SQLEnum
from sqlalchemy.orm import validates, relationship
from sqlalchemy.sql import func
from passlib.context import CryptContext
from email_validator import validate_email, EmailNotValidError
import enum
import secrets
import hashlib

from .base import BaseModel, StatusMixin


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserRole(str, enum.Enum):
    """User roles with hierarchical permissions"""
    SUPER_ADMIN = "super_admin"      # System administrator with all permissions
    ADMIN = "admin"                  # Organization administrator
    MANAGER = "manager"              # Project manager with team permissions
    DEVELOPER = "developer"          # Regular developer/user
    VIEWER = "viewer"                # Read-only access


class UserStatus(str, enum.Enum):
    """User account status"""
    ACTIVE = "active"                # Active and can use system
    INACTIVE = "inactive"            # Temporarily deactivated
    PENDING = "pending"              # Email verification pending
    SUSPENDED = "suspended"          # Suspended due to policy violation
    LOCKED = "locked"                # Locked due to security issues


class User(BaseModel, StatusMixin):
    """
    User model for authentication and profile management
    
    Includes:
    - Basic profile information (username, email, full name)
    - Authentication fields (password hash, email verification)
    - Role-based access control
    - Security features (login attempts, password reset)
    - Profile settings and preferences
    """
    
    __tablename__ = "users"
    
    # Basic Profile Information
    username = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique username for login"
    )
    
    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="User email address"
    )
    
    password_hash = Column(
        String(255),
        nullable=False,
        comment="Hashed password"
    )
    
    full_name = Column(
        String(100),
        nullable=True,
        comment="User's full display name"
    )
    
    # Authentication & Security
    role = Column(
        SQLEnum(UserRole),
        default=UserRole.DEVELOPER,
        nullable=False,
        comment="User role for access control"
    )
    
    is_email_verified = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether email address is verified"
    )
    
    email_verification_token = Column(
        String(255),
        nullable=True,
        comment="Token for email verification"
    )
    
    email_verification_expires = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Email verification token expiration"
    )
    
    # Password Reset
    password_reset_token = Column(
        String(255),
        nullable=True,
        comment="Token for password reset"
    )
    
    password_reset_expires = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Password reset token expiration"
    )
    
    password_changed_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Last password change timestamp"
    )
    
    # Security & Login Tracking
    failed_login_attempts = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of consecutive failed login attempts"
    )
    
    locked_until = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Account locked until this timestamp"
    )
    
    last_login_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last successful login timestamp"
    )
    
    last_login_ip = Column(
        String(45),  # IPv6 max length
        nullable=True,
        comment="IP address of last login"
    )
    
    # Profile & Preferences  
    avatar_url = Column(
        String(500),
        nullable=True,
        comment="URL to user avatar image"
    )
    
    bio = Column(
        Text,
        nullable=True,
        comment="User biography/description"
    )
    
    timezone = Column(
        String(50),
        default="UTC",
        nullable=False,
        comment="User's preferred timezone"
    )
    
    language = Column(
        String(10),
        default="en",
        nullable=False,
        comment="User's preferred language (ISO 639-1)"
    )
    
    # Notification Preferences (stored in metadata)
    # Example metadata structure:
    # {
    #     "notifications": {
    #         "email_on_comment": True,
    #         "email_on_mention": True,
    #         "push_notifications": False
    #     },
    #     "ui_preferences": {
    #         "theme": "light",
    #         "sidebar_collapsed": False
    #     }
    # }
    
    # Project Relationships
    # owned_projects = relationship("Project", foreign_keys="Project.owner_id", back_populates="owner")
    # created_projects = relationship("Project", foreign_keys="Project.created_by", back_populates="creator")
    # project_memberships = relationship("ProjectMember", back_populates="user")
    # uploaded_project_files = relationship("ProjectFile", back_populates="uploader")
    # sent_invitations = relationship("ProjectInvitation", foreign_keys="ProjectInvitation.inviter_id", back_populates="inviter")
    # received_invitations = relationship("ProjectInvitation", foreign_keys="ProjectInvitation.invited_user_id", back_populates="invited_user")
    
    # Development Log Relationships (will be added when model is created)
    # development_logs = relationship("DevelopmentLog", back_populates="author")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"
    
    # Password Management
    def set_password(self, password: str) -> None:
        """Hash and set password"""
        self.password_hash = pwd_context.hash(password)
        self.password_changed_at = datetime.utcnow()
        self.failed_login_attempts = 0
        self.locked_until = None
    
    def verify_password(self, password: str) -> bool:
        """Verify password against hash"""
        return pwd_context.verify(password, self.password_hash)
    
    def is_password_expired(self, max_age_days: int = 90) -> bool:
        """Check if password has expired"""
        if not self.password_changed_at:
            return True
        
        expiry_date = self.password_changed_at + timedelta(days=max_age_days)
        return datetime.utcnow() > expiry_date
    
    # Account Security
    def is_account_locked(self) -> bool:
        """Check if account is currently locked"""
        if not self.locked_until:
            return False
        return datetime.utcnow() < self.locked_until
    
    def lock_account(self, duration_minutes: int = 30) -> None:
        """Lock account for specified duration"""
        self.locked_until = datetime.utcnow() + timedelta(minutes=duration_minutes)
        self.status = UserStatus.LOCKED.value
    
    def unlock_account(self) -> None:
        """Unlock account and reset failed attempts"""
        self.locked_until = None
        self.failed_login_attempts = 0
        if self.status == UserStatus.LOCKED.value:
            self.status = UserStatus.ACTIVE.value
    
    def increment_failed_login(self, max_attempts: int = 5) -> None:
        """Increment failed login attempts and lock if threshold reached"""
        self.failed_login_attempts += 1
        
        if self.failed_login_attempts >= max_attempts:
            self.lock_account()
    
    def record_successful_login(self, ip_address: str) -> None:
        """Record successful login details"""
        self.last_login_at = datetime.utcnow()
        self.last_login_ip = ip_address
        self.failed_login_attempts = 0
        self.locked_until = None
    
    # Email Verification
    def generate_email_verification_token(self, expires_hours: int = 24) -> str:
        """Generate email verification token"""
        token = secrets.token_urlsafe(32)
        self.email_verification_token = self._hash_token(token)
        self.email_verification_expires = datetime.utcnow() + timedelta(hours=expires_hours)
        return token
    
    def verify_email_token(self, token: str) -> bool:
        """Verify email verification token"""
        if not self.email_verification_token or not self.email_verification_expires:
            return False
        
        if datetime.utcnow() > self.email_verification_expires:
            return False
        
        return self._verify_token(token, self.email_verification_token)
    
    def confirm_email(self, token: str) -> bool:
        """Confirm email address with token"""
        if self.verify_email_token(token):
            self.is_email_verified = True
            self.email_verification_token = None
            self.email_verification_expires = None
            if self.status == UserStatus.PENDING.value:
                self.status = UserStatus.ACTIVE.value
            return True
        return False
    
    # Password Reset
    def generate_password_reset_token(self, expires_hours: int = 2) -> str:
        """Generate password reset token"""
        token = secrets.token_urlsafe(32)
        self.password_reset_token = self._hash_token(token)
        self.password_reset_expires = datetime.utcnow() + timedelta(hours=expires_hours)
        return token
    
    def verify_password_reset_token(self, token: str) -> bool:
        """Verify password reset token"""
        if not self.password_reset_token or not self.password_reset_expires:
            return False
        
        if datetime.utcnow() > self.password_reset_expires:
            return False
        
        return self._verify_token(token, self.password_reset_token)
    
    def reset_password(self, token: str, new_password: str) -> bool:
        """Reset password with token"""
        if self.verify_password_reset_token(token):
            self.set_password(new_password)
            self.password_reset_token = None
            self.password_reset_expires = None
            return True
        return False
    
    # Authorization & Permissions
    def has_role(self, required_role: UserRole) -> bool:
        """Check if user has specific role or higher"""
        role_hierarchy = {
            UserRole.VIEWER: 1,
            UserRole.DEVELOPER: 2, 
            UserRole.MANAGER: 3,
            UserRole.ADMIN: 4,
            UserRole.SUPER_ADMIN: 5
        }
        
        user_level = role_hierarchy.get(UserRole(self.role), 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        return user_level >= required_level
    
    def can_access_project(self, project_id: int) -> bool:
        """Check if user can access specific project (placeholder for future implementation)"""
        # This will be implemented when Project model is created
        # For now, return True for non-viewer roles
        return self.role != UserRole.VIEWER.value
    
    def is_active_user(self) -> bool:
        """Check if user account is active and usable"""
        return (
            self.status == UserStatus.ACTIVE.value and
            not self.is_deleted and
            not self.is_account_locked()
        )
    
    # Profile Management
    def update_profile(self, **kwargs) -> None:
        """Update user profile information"""
        allowed_fields = {
            'full_name', 'bio', 'timezone', 'language', 'avatar_url'
        }
        
        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(self, field, value)
    
    def get_notification_preferences(self) -> Dict[str, Any]:
        """Get notification preferences from metadata"""
        return self.get_metadata_value('notifications', {
            'email_on_comment': True,
            'email_on_mention': True,
            'push_notifications': False,
            'email_digest': 'weekly'
        })
    
    def update_notification_preferences(self, preferences: Dict[str, Any]) -> None:
        """Update notification preferences in metadata"""
        current_prefs = self.get_notification_preferences()
        current_prefs.update(preferences)
        self.set_metadata_value('notifications', current_prefs)
    
    def get_ui_preferences(self) -> Dict[str, Any]:
        """Get UI preferences from metadata"""
        return self.get_metadata_value('ui_preferences', {
            'theme': 'light',
            'sidebar_collapsed': False,
            'items_per_page': 20
        })
    
    def update_ui_preferences(self, preferences: Dict[str, Any]) -> None:
        """Update UI preferences in metadata"""
        current_prefs = self.get_ui_preferences()
        current_prefs.update(preferences)
        self.set_metadata_value('ui_preferences', current_prefs)
    
    # Validation
    @validates('email')
    def validate_email(self, key, email):
        """Validate email format"""
        try:
            valid_email = validate_email(email)
            return valid_email.email
        except EmailNotValidError:
            raise ValueError("Invalid email address format")
    
    @validates('username')
    def validate_username(self, key, username):
        """Validate username format"""
        import re
        if not username:
            raise ValueError("Username cannot be empty")
        
        if len(username) < 3:
            raise ValueError("Username must be at least 3 characters long")
        
        if len(username) > 50:
            raise ValueError("Username cannot exceed 50 characters")
        
        # Allow alphanumeric, underscore, and hyphen
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")
        
        return username.lower()
    
    @validates('status')
    def validate_status(self, key, status):
        """Validate status against allowed values"""
        allowed_statuses = [s.value for s in UserStatus]
        if status not in allowed_statuses:
            raise ValueError(f"Status must be one of: {allowed_statuses}")
        return status
    
    @validates('role')
    def validate_role(self, key, role):
        """Validate role against allowed values"""
        if isinstance(role, str):
            try:
                role = UserRole(role)
            except ValueError:
                allowed_roles = [r.value for r in UserRole]
                raise ValueError(f"Role must be one of: {allowed_roles}")
        return role
    
    @validates('timezone')
    def validate_timezone(self, key, timezone):
        """Validate timezone string"""
        import pytz
        try:
            pytz.timezone(timezone)
            return timezone
        except pytz.exceptions.UnknownTimeZoneError:
            raise ValueError(f"Invalid timezone: {timezone}")
    
    # Utility Methods
    def to_dict(self, exclude: Optional[List[str]] = None, include_sensitive: bool = False) -> Dict[str, Any]:
        """
        Convert user to dictionary, excluding sensitive fields by default
        
        Args:
            exclude: Additional fields to exclude
            include_sensitive: Whether to include sensitive authentication fields
            
        Returns:
            Dictionary representation of user
        """
        default_exclude = ['password_hash']
        
        if not include_sensitive:
            default_exclude.extend([
                'email_verification_token',
                'password_reset_token',
                'failed_login_attempts',
                'locked_until'
            ])
        
        exclude = (exclude or []) + default_exclude
        
        result = super().to_dict(exclude=exclude)
        
        # Add computed fields
        result.update({
            'is_active': self.is_active_user(),
            'is_locked': self.is_account_locked(),
            'notification_preferences': self.get_notification_preferences(),
            'ui_preferences': self.get_ui_preferences()
        })
        
        return result
    
    @classmethod
    def create_user(
        cls,
        username: str,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        role: UserRole = UserRole.DEVELOPER,
        send_verification: bool = True
    ) -> 'User':
        """
        Factory method to create a new user
        
        Args:
            username: Unique username
            email: User email address
            password: Plain text password (will be hashed)
            full_name: Optional full name
            role: User role (default: DEVELOPER)
            send_verification: Whether to set up email verification
            
        Returns:
            New User instance (not yet saved to database)
        """
        user = cls(
            username=username,
            email=email,
            full_name=full_name,
            role=role,
            status=UserStatus.PENDING.value if send_verification else UserStatus.ACTIVE.value
        )
        
        user.set_password(password)
        
        if send_verification:
            user.generate_email_verification_token()
        else:
            user.is_email_verified = True
        
        return user
    
    # Private Helper Methods
    def _hash_token(self, token: str) -> str:
        """Hash token for secure storage"""
        return hashlib.sha256(token.encode()).hexdigest()
    
    def _verify_token(self, token: str, stored_hash: str) -> bool:
        """Verify token against stored hash"""
        token_hash = self._hash_token(token)
        return secrets.compare_digest(token_hash, stored_hash)