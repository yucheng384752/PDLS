"""
Simple project API for testing - Phase 4 T031

Simplified project endpoints without complex permissions for initial testing
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ...core.database import get_db
from ...auth import get_current_active_user
from ...models.user import User
from ...models.project import Project, ProjectStatus, ProjectPriority, ProjectType

router = APIRouter(prefix="/projects", tags=["projects-simple"])


# Pydantic schemas
from pydantic import BaseModel

class ProjectCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    project_type: str = "software"
    
class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    project_type: str
    status: str
    priority: str
    owner_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new project - simplified version"""
    
    try:
        # Create project
        project = Project(
            name=project_data.name,
            description=project_data.description,
            project_type=project_data.project_type,
            status=ProjectStatus.PLANNING,
            priority=ProjectPriority.MEDIUM,
            owner_id=current_user.id,
            created_by=current_user.id
        )
        
        db.add(project)
        db.commit()
        db.refresh(project)
        
        return ProjectResponse.from_orm(project)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create project: {str(e)}"
        )


@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List projects for current user"""
    
    # Get projects owned by or accessible to current user
    projects = db.query(Project).filter(
        Project.owner_id == current_user.id,
        Project.is_deleted == False
    ).order_by(desc(Project.created_at)).offset(skip).limit(limit).all()
    
    return [ProjectResponse.from_orm(project) for project in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get project by ID"""
    
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.is_deleted == False
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Simple access control - only owner can view
    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return ProjectResponse.from_orm(project)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_data: ProjectCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update project"""
    
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.is_deleted == False
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Only owner can update
    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    try:
        # Update fields
        project.name = project_data.name
        if project_data.description is not None:
            project.description = project_data.description
        project.project_type = project_data.project_type
        
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
    """Delete project (soft delete)"""
    
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.is_deleted == False
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Only owner can delete
    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    try:
        # Soft delete
        project.is_deleted = True
        
        db.commit()
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete project: {str(e)}"
        )