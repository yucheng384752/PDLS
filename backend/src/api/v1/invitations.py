"""
Project invitation API endpoints for PDLS

Handles project invitation system:
- Send invitations to users
- Accept/decline invitations
- Manage invitation lifecycle
"""

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_

from ...core.database import get_db
from ...auth import get_current_active_user
from ...auth.permissions import require_permission, PermissionType
from ...models.user import User
from ...models.project import (
    Project, ProjectMember, ProjectInvitation,
    ProjectMemberRole, InvitationStatus
)
from ...schemas.project import (
    ProjectInvitationCreate, ProjectInvitationResponse,
    ProjectInvitationUpdate, ProjectInvitationListResponse
)
from ...core.exceptions import (
    ProjectNotFoundError, PermissionDeniedError, 
    InvalidOperationError, ValidationError
)
from ...services.notification_service import NotificationService

router = APIRouter(prefix="/projects/{project_id}/invitations", tags=["project-invitations"])


@router.post("/", response_model=ProjectInvitationResponse, status_code=status.HTTP_201_CREATED)
async def create_invitation(
    project_id: int,
    invitation_data: ProjectInvitationCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new project invitation
    
    Requires: MANAGE_PROJECT_MEMBERS permission for the project
    """
    
    # Get project
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ProjectNotFoundError(project_id)
    
    # Check permissions
    if not await _can_manage_project_members(project, current_user):
        raise PermissionDeniedError("Insufficient permissions to invite members")
    
    # Get invited user
    invited_user = None
    if invitation_data.invited_user_id:
        invited_user = db.query(User).filter(User.id == invitation_data.invited_user_id).first()
        if not invited_user:
            raise ValidationError("Invited user not found")
    
    # Check if user is already a member
    if invited_user:
        existing_member = db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == invited_user.id,
            ProjectMember.is_deleted == False
        ).first()
        
        if existing_member:
            raise InvalidOperationError("User is already a member of this project")
    
    # Check if invitation already exists
    existing_invitation = db.query(ProjectInvitation).filter(
        ProjectInvitation.project_id == project_id,
        and_(
            ProjectInvitation.invited_user_id == invitation_data.invited_user_id if invitation_data.invited_user_id 
            else ProjectInvitation.invited_email == invitation_data.invited_email
        ),
        ProjectInvitation.status == InvitationStatus.PENDING
    ).first()
    
    if existing_invitation:
        raise InvalidOperationError("Invitation already exists for this user")
    
    try:
        # Create invitation
        invitation = ProjectInvitation(
            project_id=project_id,
            invited_user_id=invitation_data.invited_user_id,
            invited_email=invitation_data.invited_email or (invited_user.email if invited_user else None),
            invited_by=current_user.id,
            role=invitation_data.role,
            message=invitation_data.message,
            expires_at=datetime.utcnow() + timedelta(days=7)  # 7 days expiry
        )
        
        # Generate unique token
        invitation.token = str(uuid4())
        
        db.add(invitation)
        db.commit()
        db.refresh(invitation)
        
        # Send notification email (async task)
        await NotificationService.send_project_invitation_notification(
            invitation=invitation,
            project=project,
            inviter=current_user
        )
        
        return ProjectInvitationResponse.from_orm(invitation)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create invitation: {str(e)}"
        )


@router.get("/", response_model=ProjectInvitationListResponse)
async def list_invitations(
    project_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[InvitationStatus] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List project invitations
    
    Requires: VIEW_PROJECT_MEMBERS permission for the project
    """
    
    # Get project
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ProjectNotFoundError(project_id)
    
    # Check permissions
    if not await _can_view_project_members(project, current_user):
        raise PermissionDeniedError("Access denied to view project invitations")
    
    # Build query
    query = db.query(ProjectInvitation).options(
        joinedload(ProjectInvitation.invited_user),
        joinedload(ProjectInvitation.inviter)
    ).filter(ProjectInvitation.project_id == project_id)
    
    # Apply status filter
    if status_filter:
        query = query.filter(ProjectInvitation.status == status_filter)
    
    # Get total count
    total_count = query.count()
    
    # Apply pagination
    invitations = query.offset(skip).limit(limit).all()
    
    return ProjectInvitationListResponse(
        invitations=[ProjectInvitationResponse.from_orm(inv) for inv in invitations],
        total_count=total_count,
        skip=skip,
        limit=limit
    )


@router.get("/{invitation_id}", response_model=ProjectInvitationResponse)
async def get_invitation(
    project_id: int,
    invitation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get invitation details
    
    Users can view:
    - Their own invitations
    - Invitations they sent (if they can manage members)
    """
    
    invitation = db.query(ProjectInvitation).options(
        joinedload(ProjectInvitation.invited_user),
        joinedload(ProjectInvitation.inviter),
        joinedload(ProjectInvitation.project)
    ).filter(
        ProjectInvitation.id == invitation_id,
        ProjectInvitation.project_id == project_id
    ).first()
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )
    
    # Check access permissions
    can_view = (
        invitation.invited_user_id == current_user.id or  # Own invitation
        invitation.invited_by == current_user.id or       # Sent by user
        await _can_view_project_members(invitation.project, current_user)  # Can manage project
    )
    
    if not can_view:
        raise PermissionDeniedError("Access denied to view this invitation")
    
    return ProjectInvitationResponse.from_orm(invitation)


@router.put("/{invitation_id}/respond", response_model=ProjectInvitationResponse)
async def respond_to_invitation(
    project_id: int,
    invitation_id: int,
    response_data: ProjectInvitationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Accept or decline a project invitation
    
    Only the invited user can respond to their invitation
    """
    
    invitation = db.query(ProjectInvitation).options(
        joinedload(ProjectInvitation.project),
        joinedload(ProjectInvitation.inviter)
    ).filter(
        ProjectInvitation.id == invitation_id,
        ProjectInvitation.project_id == project_id
    ).first()
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )
    
    # Check if this is the invited user
    if invitation.invited_user_id != current_user.id:
        raise PermissionDeniedError("You can only respond to your own invitations")
    
    # Check if invitation is still valid
    if invitation.status != InvitationStatus.PENDING:
        raise InvalidOperationError("Invitation has already been responded to")
    
    if invitation.expires_at and datetime.utcnow() > invitation.expires_at:
        raise InvalidOperationError("Invitation has expired")
    
    try:
        # Update invitation status
        invitation.status = response_data.status
        invitation.responded_at = datetime.utcnow()
        invitation.updated_at = datetime.utcnow()
        
        # If accepted, create project membership
        if response_data.status == InvitationStatus.ACCEPTED:
            # Check if user is already a member (safety check)
            existing_member = db.query(ProjectMember).filter(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == current_user.id,
                ProjectMember.is_deleted == False
            ).first()
            
            if not existing_member:
                member = ProjectMember(
                    project_id=project_id,
                    user_id=current_user.id,
                    role=invitation.role,
                    added_by=invitation.invited_by
                )
                db.add(member)
        
        db.commit()
        db.refresh(invitation)
        
        # Send notification to inviter (async task)
        await NotificationService.send_invitation_response_notification(
            invitation=invitation,
            responder=current_user
        )
        
        return ProjectInvitationResponse.from_orm(invitation)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to respond to invitation: {str(e)}"
        )


@router.delete("/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_invitation(
    project_id: int,
    invitation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Cancel a project invitation
    
    Can be cancelled by:
    - The inviter
    - Project managers/admins
    """
    
    invitation = db.query(ProjectInvitation).options(
        joinedload(ProjectInvitation.project)
    ).filter(
        ProjectInvitation.id == invitation_id,
        ProjectInvitation.project_id == project_id
    ).first()
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )
    
    # Check permissions
    can_cancel = (
        invitation.invited_by == current_user.id or  # Inviter
        await _can_manage_project_members(invitation.project, current_user)  # Project manager
    )
    
    if not can_cancel:
        raise PermissionDeniedError("Insufficient permissions to cancel this invitation")
    
    # Check if invitation can be cancelled
    if invitation.status != InvitationStatus.PENDING:
        raise InvalidOperationError("Only pending invitations can be cancelled")
    
    try:
        # Update invitation status
        invitation.status = InvitationStatus.CANCELLED
        invitation.updated_at = datetime.utcnow()
        
        db.commit()
        
        # Send notification to invited user (async task)
        if invitation.invited_user_id:
            await NotificationService.send_invitation_cancelled_notification(
                invitation=invitation,
                cancelled_by=current_user
            )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to cancel invitation: {str(e)}"
        )


# Public endpoint for invitation token validation
@router.get("/token/{token}", response_model=ProjectInvitationResponse)
async def get_invitation_by_token(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Get invitation details by token (public endpoint)
    
    Used for email invitation links
    """
    
    invitation = db.query(ProjectInvitation).options(
        joinedload(ProjectInvitation.project),
        joinedload(ProjectInvitation.inviter)
    ).filter(
        ProjectInvitation.token == token,
        ProjectInvitation.status == InvitationStatus.PENDING
    ).first()
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired invitation token"
        )
    
    # Check if invitation has expired
    if invitation.expires_at and datetime.utcnow() > invitation.expires_at:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Invitation has expired"
        )
    
    return ProjectInvitationResponse.from_orm(invitation)


# Helper Functions

async def _can_manage_project_members(project: Project, user: User) -> bool:
    """Check if user can manage project members"""
    
    # Super admin and admin can manage all projects
    if user.has_role(require_permission(PermissionType.MANAGE_ALL_PROJECTS)):
        return True
    
    # Project owner can manage members
    if project.owner_id == user.id:
        return True
    
    # Check if user is project admin
    for member in project.members:
        if (member.user_id == user.id and 
            not member.is_deleted and 
            member.role == ProjectMemberRole.ADMIN):
            return True
    
    return False


async def _can_view_project_members(project: Project, user: User) -> bool:
    """Check if user can view project members"""
    
    # Super admin and admin can view all projects
    if user.has_role(require_permission(PermissionType.VIEW_ALL_PROJECTS)):
        return True
    
    # Project members can view member list
    for member in project.members:
        if member.user_id == user.id and not member.is_deleted:
            return True
    
    return False