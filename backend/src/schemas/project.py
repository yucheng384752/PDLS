"""
Pydantic schemas for project-related API operations in PDLS

Includes schemas for:
- Project CRUD operations
- Project member management
- Project invitations
- Project files
- Project statistics
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any, Union
from uuid import UUID

from pydantic import BaseModel, Field, validator, model_validator
from enum import Enum

from ..models.project import (
    ProjectStatus, ProjectPriority, ProjectMemberRole, 
    InvitationStatus, ProjectType
)


# Base Schemas

class ProjectBase(BaseModel):
    """Base project schema with common fields"""
    name: str = Field(..., min_length=1, max_length=200, description="Project name")
    description: Optional[str] = Field(None, max_length=2000, description="Project description")
    project_type: ProjectType = Field(..., description="Project type/category")
    status: Optional[ProjectStatus] = Field(ProjectStatus.PLANNING, description="Project status")
    priority: Optional[ProjectPriority] = Field(ProjectPriority.MEDIUM, description="Project priority")
    start_date: Optional[date] = Field(None, description="Project start date")
    end_date: Optional[date] = Field(None, description="Project end date")
    repository_url: Optional[str] = Field(None, max_length=500, description="Repository URL")
    documentation_url: Optional[str] = Field(None, max_length=500, description="Documentation URL")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional project metadata")
    
    @validator('end_date')
    def validate_end_date(cls, v, values):
        """Ensure end date is after start date"""
        if v and 'start_date' in values and values['start_date']:
            if v <= values['start_date']:
                raise ValueError('End date must be after start date')
        return v
    
    @validator('repository_url', 'documentation_url')
    def validate_url(cls, v):
        """Basic URL validation"""
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v
    
    class Config:
        use_enum_values = True


class ProjectMemberBase(BaseModel):
    """Base project member schema"""
    user_id: int = Field(..., description="User ID")
    role: ProjectMemberRole = Field(..., description="Member role in project")
    
    class Config:
        use_enum_values = True


class ProjectInvitationBase(BaseModel):
    """Base project invitation schema"""
    invited_user_id: Optional[int] = Field(None, description="Invited user ID (if registered)")
    invited_email: Optional[str] = Field(None, description="Invited user email")
    role: ProjectMemberRole = Field(..., description="Invited user role")
    message: Optional[str] = Field(None, max_length=500, description="Invitation message")
    
    @model_validator(mode='after')
    def validate_invitation_target(self):
        """Ensure either user_id or email is provided"""
        if not self.invited_user_id and not self.invited_email:
            raise ValueError('Either invited_user_id or invited_email must be provided')
        
        return self
    
    class Config:
        use_enum_values = True


# Create Schemas

class ProjectCreate(ProjectBase):
    """Schema for creating a new project"""
    pass


class ProjectMemberCreate(ProjectMemberBase):
    """Schema for adding a new project member"""
    pass


class ProjectInvitationCreate(ProjectInvitationBase):
    """Schema for creating a new project invitation"""
    pass


# Update Schemas

class ProjectUpdate(BaseModel):
    """Schema for updating project information"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    status: Optional[ProjectStatus] = None
    priority: Optional[ProjectPriority] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    repository_url: Optional[str] = Field(None, max_length=500)
    documentation_url: Optional[str] = Field(None, max_length=500)
    metadata: Optional[Dict[str, Any]] = None
    
    @validator('end_date')
    def validate_end_date(cls, v, values):
        """Ensure end date is after start date if both provided"""
        if v and 'start_date' in values and values['start_date']:
            if v <= values['start_date']:
                raise ValueError('End date must be after start date')
        return v
    
    @validator('repository_url', 'documentation_url')
    def validate_url(cls, v):
        """Basic URL validation"""
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v
    
    class Config:
        use_enum_values = True


class ProjectMemberUpdate(BaseModel):
    """Schema for updating project member information"""
    role: ProjectMemberRole = Field(..., description="New member role")
    
    class Config:
        use_enum_values = True


class ProjectInvitationUpdate(BaseModel):
    """Schema for responding to project invitation"""
    status: InvitationStatus = Field(..., description="Invitation response")
    
    @validator('status')
    def validate_response_status(cls, v):
        """Ensure only valid response statuses are allowed"""
        if v not in [InvitationStatus.ACCEPTED, InvitationStatus.DECLINED]:
            raise ValueError('Status must be ACCEPTED or DECLINED')
        return v
    
    class Config:
        use_enum_values = True


# Response Schemas

class UserSummary(BaseModel):
    """Summary user information for responses"""
    id: int
    username: str
    email: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    
    class Config:
        from_attributes = True


class ProjectResponse(ProjectBase):
    """Schema for project response"""
    id: int
    uuid: UUID
    owner_id: int
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime]
    is_deleted: bool
    
    # Related data
    owner: Optional[UserSummary] = None
    creator: Optional[UserSummary] = None
    
    class Config:
        from_attributes = True


class ProjectMemberResponse(ProjectMemberBase):
    """Schema for project member response"""
    id: int
    project_id: int
    joined_at: datetime
    added_by: int
    created_at: datetime
    updated_at: Optional[datetime]
    is_deleted: bool
    
    # Related data
    user: Optional[UserSummary] = None
    added_by_user: Optional[UserSummary] = None
    
    class Config:
        from_attributes = True


class ProjectInvitationResponse(ProjectInvitationBase):
    """Schema for project invitation response"""
    id: int
    project_id: int
    token: Optional[str] = None  # Only shown to inviter or system admin
    status: InvitationStatus
    expires_at: Optional[datetime]
    responded_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]
    
    # Related data
    project: Optional[ProjectResponse] = None
    invited_user: Optional[UserSummary] = None
    inviter: Optional[UserSummary] = None
    
    class Config:
        from_attributes = True


class ProjectFileResponse(BaseModel):
    """Schema for project file response"""
    id: int
    project_id: int
    filename: str
    original_filename: str
    file_size: int
    mime_type: str
    file_path: str
    uploader_id: int
    upload_date: datetime
    description: Optional[str]
    tags: List[str]
    metadata: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: Optional[datetime]
    is_deleted: bool
    
    # Related data
    uploader: Optional[UserSummary] = None
    
    class Config:
        from_attributes = True


class ProjectDetailResponse(ProjectResponse):
    """Detailed project response with related data"""
    members: List[ProjectMemberResponse] = []
    files: List[ProjectFileResponse] = []
    invitations: List[ProjectInvitationResponse] = []
    
    class Config:
        from_attributes = True


# List Response Schemas

class ProjectListResponse(BaseModel):
    """Schema for paginated project list response"""
    projects: List[ProjectResponse]
    total_count: int
    skip: int
    limit: int
    
    class Config:
        from_attributes = True


class ProjectInvitationListResponse(BaseModel):
    """Schema for paginated invitation list response"""
    invitations: List[ProjectInvitationResponse]
    total_count: int
    skip: int
    limit: int
    
    class Config:
        from_attributes = True


# Statistics Schemas

class ProjectStatsResponse(BaseModel):
    """Schema for project statistics response"""
    project_id: int
    member_count: int
    file_count: int
    log_count: int
    last_activity: datetime
    
    class Config:
        from_attributes = True


class ProjectDashboardStats(BaseModel):
    """Schema for user dashboard project statistics"""
    total_projects: int
    owned_projects: int
    member_projects: int
    active_projects: int
    completed_projects: int
    pending_invitations: int
    
    class Config:
        from_attributes = True


# File Upload Schemas

class ProjectFileUpload(BaseModel):
    """Schema for project file upload metadata"""
    description: Optional[str] = Field(None, max_length=500)
    tags: List[str] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None
    
    @validator('tags')
    def validate_tags(cls, v):
        """Validate tags format"""
        if len(v) > 10:
            raise ValueError('Maximum 10 tags allowed')
        
        for tag in v:
            if not isinstance(tag, str) or len(tag.strip()) == 0:
                raise ValueError('Tags must be non-empty strings')
            if len(tag) > 50:
                raise ValueError('Tag length cannot exceed 50 characters')
        
        return [tag.strip() for tag in v]
    
    class Config:
        from_attributes = True


# Search and Filter Schemas

class ProjectSearchRequest(BaseModel):
    """Schema for project search request"""
    search_term: Optional[str] = Field(None, max_length=100)
    status_filter: Optional[List[ProjectStatus]] = None
    priority_filter: Optional[List[ProjectPriority]] = None
    project_type_filter: Optional[List[ProjectType]] = None
    owner_ids: Optional[List[int]] = None
    member_ids: Optional[List[int]] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    include_deleted: bool = False
    
    @validator('date_to')
    def validate_date_range(cls, v, values):
        """Ensure date_to is after date_from"""
        if v and 'date_from' in values and values['date_from']:
            if v <= values['date_from']:
                raise ValueError('date_to must be after date_from')
        return v
    
    class Config:
        use_enum_values = True


class ProjectSortRequest(BaseModel):
    """Schema for project sorting request"""
    sort_by: str = Field("created_at", description="Field to sort by")
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="Sort order")
    
    @validator('sort_by')
    def validate_sort_field(cls, v):
        """Validate sort field"""
        allowed_fields = [
            'name', 'created_at', 'updated_at', 'start_date', 
            'end_date', 'status', 'priority', 'project_type'
        ]
        if v not in allowed_fields:
            raise ValueError(f'Sort field must be one of: {allowed_fields}')
        return v
    
    class Config:
        from_attributes = True


# Bulk Operations Schemas

class BulkProjectUpdate(BaseModel):
    """Schema for bulk project updates"""
    project_ids: List[int] = Field(..., min_items=1, max_items=50)
    updates: ProjectUpdate
    
    @validator('project_ids')
    def validate_project_ids(cls, v):
        """Validate project IDs"""
        if len(set(v)) != len(v):
            raise ValueError('Duplicate project IDs not allowed')
        return v
    
    class Config:
        from_attributes = True


class BulkMemberOperation(BaseModel):
    """Schema for bulk member operations"""
    user_ids: List[int] = Field(..., min_items=1, max_items=20)
    role: ProjectMemberRole
    
    @validator('user_ids')
    def validate_user_ids(cls, v):
        """Validate user IDs"""
        if len(set(v)) != len(v):
            raise ValueError('Duplicate user IDs not allowed')
        return v
    
    class Config:
        use_enum_values = True


# Export Schemas

class ProjectExportRequest(BaseModel):
    """Schema for project export request"""
    project_ids: Optional[List[int]] = None
    include_members: bool = True
    include_files: bool = True
    include_logs: bool = True
    format: str = Field("json", pattern="^(json|csv|excel)$")
    date_range: Optional[Dict[str, date]] = None
    
    class Config:
        from_attributes = True