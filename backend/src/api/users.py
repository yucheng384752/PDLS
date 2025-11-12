"""User management API endpoints with RBAC protection"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from src.models.user import User, UserRole, UserStatus
from src.schemas.user import (
    UserResponse, 
    UserListResponse, 
    UserUpdateRequest,
    UserCreateRequest,
    UserRoleUpdateRequest
)
from src.auth import (
    get_current_active_user,
    get_admin_user,
    get_manager_user,
    require_permission,
    require_role,
    Permission,
    PermissionChecker,
    check_user_management_permission
)
from src.core.database import get_db

router = APIRouter(prefix="/api/users", tags=["User Management"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user's profile"""
    return UserResponse.from_orm(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    user_data: UserUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user's profile"""
    # Users can always update their own profile (basic info only)
    
    # Update allowed fields
    for field, value in user_data.dict(exclude_unset=True).items():
        if field in ['full_name', 'timezone', 'language', 'phone']:
            setattr(current_user, field, value)
    
    current_user.updated_at = func.now()
    
    await db.commit()
    await db.refresh(current_user)
    
    return UserResponse.from_orm(current_user)


@router.get("/", response_model=UserListResponse)
async def list_users(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    role: Optional[UserRole] = Query(None, description="Filter by user role"),
    status: Optional[UserStatus] = Query(None, description="Filter by user status"),
    search: Optional[str] = Query(None, description="Search in username, email, or full name"),
    current_user: User = Depends(get_manager_user),  # Requires manager+ level
    db: AsyncSession = Depends(get_db)
):
    """List users with filtering and pagination (Manager+ access required)"""
    
    # Build query
    query = select(User).where(User.is_deleted == False)
    
    # Apply filters
    if role:
        query = query.where(User.role == role.value)
    
    if status:
        query = query.where(User.status == status.value)
    
    if search:
        search_term = f"%{search}%"
        query = query.where(
            and_(
                User.username.ilike(search_term) |
                User.email.ilike(search_term) |
                User.full_name.ilike(search_term)
            )
        )
    
    # Get total count
    count_query = select(func.count(User.id)).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar()
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    
    # Execute query
    result = await db.execute(query)
    users = result.scalars().all()
    
    return UserListResponse(
        users=[UserResponse.from_orm(user) for user in users],
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user by ID (Manager+ can view all, others only themselves)"""
    
    # Get target user
    query = select(User).where(and_(User.id == user_id, User.is_deleted == False))
    result = await db.execute(query)
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check access permissions
    if current_user.id != user.id and not PermissionChecker.has_role_level(
        UserRole(current_user.role), UserRole.MANAGER
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this user"
        )
    
    return UserResponse.from_orm(user)


@router.post("/", response_model=UserResponse)
async def create_user(
    user_data: UserCreateRequest,
    current_user: User = Depends(get_admin_user),  # Admin+ access required
    db: AsyncSession = Depends(get_db)
):
    """Create new user (Admin+ access required)"""
    
    # Check if user already exists
    existing_query = select(User).where(
        and_(
            (User.username == user_data.username) | (User.email == user_data.email),
            User.is_deleted == False
        )
    )
    result = await db.execute(existing_query)
    existing_user = result.scalars().first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this username or email already exists"
        )
    
    # Create new user
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        role=user_data.role.value,
        status=UserStatus.ACTIVE.value,
        timezone=user_data.timezone or "UTC",
        language=user_data.language or "en",
        phone=user_data.phone
    )
    
    # Set password
    new_user.set_password(user_data.password)
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return UserResponse.from_orm(new_user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user (Users can update themselves, Managers+ can update others)"""
    
    # Get target user
    query = select(User).where(and_(User.id == user_id, User.is_deleted == False))
    result = await db.execute(query)
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check permissions
    if not check_user_management_permission(current_user, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user"
        )
    
    # Update allowed fields
    allowed_fields = {'full_name', 'timezone', 'language', 'phone'}
    
    # Managers+ can update additional fields
    if PermissionChecker.has_role_level(UserRole(current_user.role), UserRole.MANAGER):
        allowed_fields.update({'status'})
    
    for field, value in user_data.dict(exclude_unset=True).items():
        if field in allowed_fields:
            setattr(user, field, value)
    
    user.updated_at = func.now()
    
    await db.commit()
    await db.refresh(user)
    
    return UserResponse.from_orm(user)


@router.put("/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: int,
    role_data: UserRoleUpdateRequest,
    current_user: User = Depends(get_admin_user),  # Admin+ access required
    db: AsyncSession = Depends(get_db)
):
    """Update user role (Admin+ access required)"""
    
    # Get target user
    query = select(User).where(and_(User.id == user_id, User.is_deleted == False))
    result = await db.execute(query)
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if current user can assign this role
    if not PermissionChecker.can_manage_user(
        UserRole(current_user.role), 
        role_data.role
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Not authorized to assign role: {role_data.role.value}"
        )
    
    # Update role
    user.role = role_data.role.value
    user.updated_at = func.now()
    
    await db.commit()
    await db.refresh(user)
    
    return UserResponse.from_orm(user)


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_admin_user),  # Admin+ access required
    db: AsyncSession = Depends(get_db)
):
    """Soft delete user (Admin+ access required)"""
    
    # Get target user
    query = select(User).where(and_(User.id == user_id, User.is_deleted == False))
    result = await db.execute(query)
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent self-deletion
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    # Check if current user can delete this user
    if not PermissionChecker.can_manage_user(
        UserRole(current_user.role), 
        UserRole(user.role)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this user"
        )
    
    # Soft delete
    user.is_deleted = True
    user.deleted_at = func.now()
    user.updated_at = func.now()
    
    await db.commit()
    
    return {"message": "User deleted successfully"}


@router.get("/{user_id}/permissions")
async def get_user_permissions(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's effective permissions"""
    
    # Get target user
    query = select(User).where(and_(User.id == user_id, User.is_deleted == False))
    result = await db.execute(query)
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check access (users can view their own permissions, managers+ can view others')
    if (user.id != current_user.id and 
        not PermissionChecker.has_role_level(UserRole(current_user.role), UserRole.MANAGER)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view user permissions"
        )
    
    # Get user permissions
    user_role = UserRole(user.role)
    permissions = PermissionChecker.get_user_permissions(user_role)
    
    return {
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "permissions": list(permissions)
    }


@router.post("/avatar", response_model=dict)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload user avatar"""
    import os
    import uuid
    from PIL import Image
    from io import BytesIO
    
    # Validate file type
    allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only JPEG, PNG, GIF, and WebP are allowed."
        )
    
    # Validate file size (5MB max)
    max_size = 5 * 1024 * 1024  # 5MB
    file_content = await file.read()
    if len(file_content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size is 5MB."
        )
    
    try:
        # Process image
        image = Image.open(BytesIO(file_content))
        
        # Convert to RGB if necessary
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
            image = background
        
        # Resize image to 256x256
        image.thumbnail((256, 256), Image.Resampling.LANCZOS)
        
        # Generate unique filename
        file_extension = 'jpg'  # Always save as JPEG
        filename = f"avatar_{current_user.id}_{uuid.uuid4().hex}.{file_extension}"
        
        # Create upload directory if it doesn't exist
        upload_dir = "uploads/avatars"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save image
        file_path = os.path.join(upload_dir, filename)
        image.save(file_path, 'JPEG', quality=90, optimize=True)
        
        # Update user avatar URL in database
        avatar_url = f"/static/avatars/{filename}"
        current_user.avatar_url = avatar_url
        current_user.updated_at = func.now()
        
        await db.commit()
        
        return {
            "message": "Avatar uploaded successfully",
            "avatar_url": avatar_url
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing image: {str(e)}"
        )


@router.delete("/avatar")
async def delete_avatar(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete user avatar"""
    import os
    
    if not current_user.avatar_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No avatar found"
        )
    
    try:
        # Extract filename from avatar URL
        if current_user.avatar_url.startswith("/static/avatars/"):
            filename = current_user.avatar_url.replace("/static/avatars/", "")
            file_path = os.path.join("uploads/avatars", filename)
            
            # Delete file if it exists
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # Remove avatar URL from database
        current_user.avatar_url = None
        current_user.updated_at = func.now()
        
        await db.commit()
        
        return {"message": "Avatar deleted successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting avatar: {str(e)}"
        )