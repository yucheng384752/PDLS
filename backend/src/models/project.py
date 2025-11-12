"""
Project data models for PDLS backend
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from .base import BaseModel


class ProjectStatus(str, Enum):
    """Project status enumeration"""
    PLANNING = "planning"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


class ProjectPriority(str, Enum):
    """Project priority enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ProjectType(str, Enum):
    """Project type enumeration"""
    SOFTWARE = "software"
    WEB = "web"
    MOBILE = "mobile"
    DATA_SCIENCE = "data_science"
    INFRASTRUCTURE = "infrastructure"
    RESEARCH = "research"
    OTHER = "other"


class ProjectMemberRole(str, Enum):
    """Project member role enumeration"""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class InvitationStatus(str, Enum):
    """Project invitation status enumeration"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class Project(BaseModel):
    """Project model representing development projects"""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    
    # Basic Information
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    short_description = Column(String(500), nullable=True)
    
    # Project Classification
    project_type = Column(SQLEnum(ProjectType), default=ProjectType.SOFTWARE, nullable=False)
    status = Column(SQLEnum(ProjectStatus), default=ProjectStatus.PLANNING, nullable=False)
    priority = Column(SQLEnum(ProjectPriority), default=ProjectPriority.MEDIUM, nullable=False)
    
    # Project Metadata
    project_code = Column(String(50), unique=True, nullable=True, index=True)  # e.g., "PDLS-2024"
    version = Column(String(50), default="1.0.0", nullable=False)
    tags = Column(String(500), nullable=True)  # JSON string of tags
    
    # Dates and Timeline
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    estimated_hours = Column(Integer, nullable=True)
    actual_hours = Column(Integer, default=0)
    
    # Repository and External Links
    repository_url = Column(String(500), nullable=True)
    documentation_url = Column(String(500), nullable=True)
    deployment_url = Column(String(500), nullable=True)
    
    # Project Settings
    is_public = Column(Boolean, default=False, nullable=False)
    allow_external_contributors = Column(Boolean, default=False, nullable=False)
    require_approval_for_logs = Column(Boolean, default=False, nullable=False)
    
    # Owner Information
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    owner = relationship("User", foreign_keys=[owner_id], back_populates="owned_projects")
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_projects")
    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    # development_logs = relationship("DevelopmentLog", back_populates="project", cascade="all, delete-orphan")  # TODO: Add when DevelopmentLog model is created
    project_files = relationship("ProjectFile", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.name}', status='{self.status}')>"


class ProjectMember(BaseModel):
    """Project member association model"""
    __tablename__ = "project_members"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Member Information
    role = Column(SQLEnum(ProjectMemberRole), default=ProjectMemberRole.MEMBER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Permissions
    can_create_logs = Column(Boolean, default=True, nullable=False)
    can_edit_logs = Column(Boolean, default=False, nullable=False)
    can_delete_logs = Column(Boolean, default=False, nullable=False)
    can_manage_members = Column(Boolean, default=False, nullable=False)
    can_edit_project = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="members")
    user = relationship("User", back_populates="project_memberships")

    def __repr__(self):
        return f"<ProjectMember(project_id={self.project_id}, user_id={self.user_id}, role='{self.role}')>"


class ProjectFile(BaseModel):
    """Project file model for document and asset management"""
    __tablename__ = "project_files"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # File Information
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)  # MinIO path
    file_size = Column(Integer, nullable=False)  # Size in bytes
    mime_type = Column(String(100), nullable=False)
    
    # File Metadata
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)  # e.g., "documentation", "assets", "code"
    tags = Column(String(500), nullable=True)  # JSON string of tags
    
    # File Status
    is_public = Column(Boolean, default=False, nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="project_files")
    uploader = relationship("User", back_populates="uploaded_project_files")

    def __repr__(self):
        return f"<ProjectFile(id={self.id}, filename='{self.filename}', project_id={self.project_id})>"


class ProjectInvitation(BaseModel):
    """Project invitation model for member invitations"""
    __tablename__ = "project_invitations"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    
    # Foreign Keys
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    inviter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    invited_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Can be null for email invitations
    
    # Invitation Information
    email = Column(String(255), nullable=False, index=True)
    role = Column(SQLEnum(ProjectMemberRole), default=ProjectMemberRole.MEMBER, nullable=False)
    message = Column(Text, nullable=True)
    
    # Invitation Status
    status = Column(String(20), default="pending", nullable=False)  # pending, accepted, rejected, expired
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)  # 7 days from creation
    responded_at = Column(DateTime, nullable=True)
    
    # Relationships
    project = relationship("Project")
    inviter = relationship("User", foreign_keys=[inviter_id])
    invited_user = relationship("User", foreign_keys=[invited_user_id])

    def __repr__(self):
        return f"<ProjectInvitation(id={self.id}, email='{self.email}', status='{self.status}')>"