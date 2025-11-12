"""
Project API endpoints for PDLS

Provides CRUD operations for projects, including:
- Create/read/update/delete projects
- Project member management
- Project file operations
- Project invitation system
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, selectinload, joinedload
from sqlalchemy import and_, or_, desc, asc

from ...core.database import get_db
from ...auth import get_current_user, get_current_active_user
from ...auth.permissions import require_permission, Permission
from ...models.user import User
from ...models.project import (
    Project, ProjectMember, ProjectFile, ProjectInvitation,
    ProjectStatus, ProjectPriority, ProjectMemberRole
)
from ...schemas.project import (
    ProjectCreate, ProjectUpdate, ProjectResponse, ProjectDetailResponse,
    ProjectMemberCreate, ProjectMemberUpdate, ProjectMemberResponse,
    ProjectInvitationCreate, ProjectInvitationResponse,
    ProjectFileResponse, ProjectListResponse, ProjectStatsResponse
)
from ...core.exceptions import (
    ProjectNotFoundError, PermissionDeniedError, 
    InvalidOperationError, ValidationError
)
from ...core.config import settings
from ...services.file_service import FileService
from ...services.notification_service import NotificationService

router = APIRouter(prefix="/projects", tags=["projects"])


# Project CRUD Operations

@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new project
    
    Requires: CREATE_PROJECT permission
    """
    # Check permissions
    if not current_user.has_role(require_permission(PermissionType.CREATE_PROJECT)):
        raise PermissionDeniedError("Insufficient permissions to create project")
    
    try:
        # Create project
        project = Project(
            name=project_data.name,
            description=project_data.description,
            project_type=project_data.project_type,
            status=project_data.status or ProjectStatus.PLANNING,
            priority=project_data.priority or ProjectPriority.MEDIUM,
            owner_id=current_user.id,
            created_by=current_user.id,
            start_date=project_data.start_date,
            end_date=project_data.end_date,
            repository_url=project_data.repository_url,
            documentation_url=project_data.documentation_url
        )
        
        # Set metadata if provided
        if project_data.metadata:
            project.metadata = project_data.metadata
        
        db.add(project)
        db.flush()  # Get the project ID
        
        # Add owner as project admin
        project_member = ProjectMember(
            project_id=project.id,
            user_id=current_user.id,
            role=ProjectMemberRole.ADMIN,
            added_by=current_user.id
        )
        
        db.add(project_member)
        db.commit()
        db.refresh(project)
        
        # Send notification (async task)
        await NotificationService.send_project_created_notification(
            project=project,
            creator=current_user
        )
        
        return ProjectResponse.from_orm(project)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create project: {str(e)}"
        )


@router.get("/", response_model=ProjectListResponse)
async def list_projects(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of records to return"),
    status_filter: Optional[ProjectStatus] = Query(None, description="Filter by project status"),
    priority_filter: Optional[ProjectPriority] = Query(None, description="Filter by project priority"),
    search: Optional[str] = Query(None, description="Search in project name and description"),
    owner_id: Optional[int] = Query(None, description="Filter by owner ID"),
    member_id: Optional[int] = Query(None, description="Filter by member ID"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List projects with filtering and pagination
    
    Users can see:
    - Projects they own
    - Projects they are members of
    - All projects (if admin)
    """
    
    # Base query
    query = db.query(Project).options(
        joinedload(Project.owner),
        joinedload(Project.creator),
        selectinload(Project.members).joinedload(ProjectMember.user)
    )
    
    # Apply access control
    if not current_user.has_role(require_permission(PermissionType.VIEW_ALL_PROJECTS)):
        # Non-admin users can only see their own projects or projects they're members of
        query = query.join(ProjectMember).filter(
            or_(
                Project.owner_id == current_user.id,
                ProjectMember.user_id == current_user.id
            )
        )
    
    # Apply filters
    if status_filter:
        query = query.filter(Project.status == status_filter)
    
    if priority_filter:
        query = query.filter(Project.priority == priority_filter)
    
    if owner_id:
        query = query.filter(Project.owner_id == owner_id)
    
    if member_id:
        query = query.join(ProjectMember).filter(ProjectMember.user_id == member_id)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Project.name.ilike(search_term),
                Project.description.ilike(search_term)
            )
        )
    
    # Apply sorting
    if hasattr(Project, sort_by):
        sort_column = getattr(Project, sort_by)
        if sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
    
    # Get total count
    total_count = query.count()
    
    # Apply pagination
    projects = query.offset(skip).limit(limit).all()
    
    return ProjectListResponse(
        projects=[ProjectResponse.from_orm(project) for project in projects],
        total_count=total_count,
        skip=skip,
        limit=limit
    )


@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get project details by ID
    
    Requires: VIEW_PROJECT permission for the specific project
    """
    
    # Get project with related data
    project = db.query(Project).options(
        joinedload(Project.owner),
        joinedload(Project.creator),
        selectinload(Project.members).joinedload(ProjectMember.user),
        selectinload(Project.files).joinedload(ProjectFile.uploader),
        selectinload(Project.invitations).joinedload(ProjectInvitation.invited_user)
    ).filter(Project.id == project_id).first()
    
    if not project:
        raise ProjectNotFoundError(project_id)
    
    # Check access permissions
    if not await _can_access_project(project, current_user, PermissionType.VIEW_PROJECT):
        raise PermissionDeniedError("Access denied to this project")
    
    return ProjectDetailResponse.from_orm(project)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update project information
    
    Requires: EDIT_PROJECT permission for the specific project
    """
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ProjectNotFoundError(project_id)
    
    # Check permissions
    if not await _can_access_project(project, current_user, PermissionType.EDIT_PROJECT):
        raise PermissionDeniedError("Insufficient permissions to edit this project")
    
    try:
        # Update fields
        update_data = project_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            if field != "metadata":
                setattr(project, field, value)
        
        # Handle metadata update
        if "metadata" in update_data:
            if project.metadata:
                project.metadata.update(update_data["metadata"])
            else:
                project.metadata = update_data["metadata"]
        
        project.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(project)
        
        return ProjectResponse.from_orm(project)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update project: {str(e)}"
        )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a project (soft delete)
    
    Requires: DELETE_PROJECT permission for the specific project
    """
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ProjectNotFoundError(project_id)
    
    # Check permissions
    if not await _can_access_project(project, current_user, PermissionType.DELETE_PROJECT):
        raise PermissionDeniedError("Insufficient permissions to delete this project")
    
    try:
        # Soft delete
        project.soft_delete()
        
        db.commit()
        
        # Send notification (async task)
        await NotificationService.send_project_deleted_notification(
            project=project,
            deleted_by=current_user
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete project: {str(e)}"
        )


# Project Member Management

@router.get("/{project_id}/members", response_model=List[ProjectMemberResponse])
async def list_project_members(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List project members
    
    Requires: VIEW_PROJECT_MEMBERS permission for the specific project
    """
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ProjectNotFoundError(project_id)
    
    # Check permissions
    if not await _can_access_project(project, current_user, PermissionType.VIEW_PROJECT_MEMBERS):
        raise PermissionDeniedError("Access denied to view project members")
    
    members = db.query(ProjectMember).options(
        joinedload(ProjectMember.user),
        joinedload(ProjectMember.added_by_user)
    ).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.is_deleted == False
    ).all()
    
    return [ProjectMemberResponse.from_orm(member) for member in members]


@router.post("/{project_id}/members", response_model=ProjectMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_project_member(
    project_id: int,
    member_data: ProjectMemberCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Add a new project member
    
    Requires: MANAGE_PROJECT_MEMBERS permission for the specific project
    """
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ProjectNotFoundError(project_id)
    
    # Check permissions
    if not await _can_access_project(project, current_user, PermissionType.MANAGE_PROJECT_MEMBERS):
        raise PermissionDeniedError("Insufficient permissions to manage project members")
    
    # Check if user exists
    user = db.query(User).filter(User.id == member_data.user_id).first()
    if not user:
        raise ValidationError("User not found")
    
    # Check if user is already a member
    existing_member = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == member_data.user_id,
        ProjectMember.is_deleted == False
    ).first()
    
    if existing_member:
        raise InvalidOperationError("User is already a member of this project")
    
    try:
        # Create new member
        member = ProjectMember(
            project_id=project_id,
            user_id=member_data.user_id,
            role=member_data.role,
            added_by=current_user.id
        )
        
        db.add(member)
        db.commit()
        db.refresh(member)
        
        # Send notification (async task)
        await NotificationService.send_project_member_added_notification(
            project=project,
            new_member=user,
            added_by=current_user
        )
        
        return ProjectMemberResponse.from_orm(member)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to add project member: {str(e)}"
        )


@router.put("/{project_id}/members/{member_id}", response_model=ProjectMemberResponse)
async def update_project_member(
    project_id: int,
    member_id: int,
    member_data: ProjectMemberUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update project member role
    
    Requires: MANAGE_PROJECT_MEMBERS permission for the specific project
    """
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ProjectNotFoundError(project_id)
    
    # Check permissions
    if not await _can_access_project(project, current_user, PermissionType.MANAGE_PROJECT_MEMBERS):
        raise PermissionDeniedError("Insufficient permissions to manage project members")
    
    member = db.query(ProjectMember).filter(
        ProjectMember.id == member_id,
        ProjectMember.project_id == project_id,
        ProjectMember.is_deleted == False
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project member not found"
        )
    
    try:
        # Update member role
        member.role = member_data.role
        member.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(member)
        
        return ProjectMemberResponse.from_orm(member)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update project member: {str(e)}"
        )


@router.delete("/{project_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_project_member(
    project_id: int,
    member_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Remove a project member
    
    Requires: MANAGE_PROJECT_MEMBERS permission for the specific project
    """
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ProjectNotFoundError(project_id)
    
    # Check permissions
    if not await _can_access_project(project, current_user, PermissionType.MANAGE_PROJECT_MEMBERS):
        raise PermissionDeniedError("Insufficient permissions to manage project members")
    
    member = db.query(ProjectMember).filter(
        ProjectMember.id == member_id,
        ProjectMember.project_id == project_id,
        ProjectMember.is_deleted == False
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project member not found"
        )
    
    # Prevent removing the project owner
    if member.user_id == project.owner_id:
        raise InvalidOperationError("Cannot remove project owner from project")
    
    try:
        # Soft delete member
        member.soft_delete()
        
        db.commit()
        
        # Send notification (async task)
        await NotificationService.send_project_member_removed_notification(
            project=project,
            removed_member=member.user,
            removed_by=current_user
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to remove project member: {str(e)}"
        )


# Project Statistics

@router.get("/{project_id}/stats", response_model=ProjectStatsResponse)
async def get_project_stats(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get project statistics
    
    Requires: VIEW_PROJECT permission for the specific project
    """
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ProjectNotFoundError(project_id)
    
    # Check permissions
    if not await _can_access_project(project, current_user, PermissionType.VIEW_PROJECT):
        raise PermissionDeniedError("Access denied to view project statistics")
    
    # Calculate statistics
    member_count = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.is_deleted == False
    ).count()
    
    file_count = db.query(ProjectFile).filter(
        ProjectFile.project_id == project_id,
        ProjectFile.is_deleted == False
    ).count()
    
    # TODO: Add development log statistics when model is implemented
    log_count = 0
    
    return ProjectStatsResponse(
        project_id=project_id,
        member_count=member_count,
        file_count=file_count,
        log_count=log_count,
        last_activity=project.updated_at or project.created_at
    )


# Helper Functions

async def _can_access_project(
    project: Project, 
    user: User, 
    required_permission: PermissionType
) -> bool:
    """
    Check if user can perform specific action on project
    
    Args:
        project: Project instance
        user: User instance
        required_permission: Required permission type
        
    Returns:
        True if user has access, False otherwise
    """
    
    # Super admin and admin can access all projects
    if user.has_role(require_permission(PermissionType.VIEW_ALL_PROJECTS)):
        return True
    
    # Project owner has all permissions
    if project.owner_id == user.id:
        return True
    
    # Check project member permissions
    # This is a simplified version - in a real implementation,
    # you would have more granular role-based permissions
    member = None
    for m in project.members:
        if m.user_id == user.id and not m.is_deleted:
            member = m
            break
    
    if not member:
        return False
    
    # Define permission mapping based on member role
    permission_map = {
        ProjectMemberRole.ADMIN: [
            PermissionType.VIEW_PROJECT,
            PermissionType.EDIT_PROJECT,
            PermissionType.VIEW_PROJECT_MEMBERS,
            PermissionType.MANAGE_PROJECT_MEMBERS,
            PermissionType.UPLOAD_PROJECT_FILES,
            PermissionType.DELETE_PROJECT_FILES
        ],
        ProjectMemberRole.MEMBER: [
            PermissionType.VIEW_PROJECT,
            PermissionType.VIEW_PROJECT_MEMBERS,
            PermissionType.UPLOAD_PROJECT_FILES
        ],
        ProjectMemberRole.VIEWER: [
            PermissionType.VIEW_PROJECT,
            PermissionType.VIEW_PROJECT_MEMBERS
        ]
    }
    
    allowed_permissions = permission_map.get(member.role, [])
    return required_permission in allowed_permissions