"""
File service for PDLS

Handles file operations:
- File upload and storage
- File validation
- File metadata management
- File access control
"""

import logging
import os
import uuid
import mimetypes
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from pathlib import Path

from fastapi import UploadFile, HTTPException, status
from ..core.config import settings

logger = logging.getLogger(__name__)


class FileService:
    """Service for handling file operations"""
    
    # Allowed file types and their maximum sizes (in bytes)
    ALLOWED_FILE_TYPES = {
        # Images
        'image/jpeg': 5 * 1024 * 1024,      # 5MB
        'image/png': 5 * 1024 * 1024,       # 5MB
        'image/gif': 2 * 1024 * 1024,       # 2MB
        'image/webp': 5 * 1024 * 1024,      # 5MB
        
        # Documents
        'application/pdf': 10 * 1024 * 1024,  # 10MB
        'application/msword': 10 * 1024 * 1024,  # 10MB
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 10 * 1024 * 1024,  # 10MB
        'application/vnd.ms-excel': 10 * 1024 * 1024,  # 10MB
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 10 * 1024 * 1024,  # 10MB
        'application/vnd.ms-powerpoint': 10 * 1024 * 1024,  # 10MB
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': 10 * 1024 * 1024,  # 10MB
        
        # Text files
        'text/plain': 1 * 1024 * 1024,       # 1MB
        'text/csv': 5 * 1024 * 1024,         # 5MB
        'application/json': 1 * 1024 * 1024,  # 1MB
        'application/xml': 1 * 1024 * 1024,   # 1MB
        
        # Archives
        'application/zip': 50 * 1024 * 1024,  # 50MB
        'application/x-rar-compressed': 50 * 1024 * 1024,  # 50MB
        'application/x-7z-compressed': 50 * 1024 * 1024,   # 50MB
        
        # Code files (common extensions)
        'text/x-python': 1 * 1024 * 1024,    # 1MB
        'text/javascript': 1 * 1024 * 1024,  # 1MB
        'text/html': 1 * 1024 * 1024,        # 1MB
        'text/css': 1 * 1024 * 1024,         # 1MB
    }
    
    # File type categories for easier management
    FILE_CATEGORIES = {
        'image': ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
        'document': [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-powerpoint',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation'
        ],
        'text': ['text/plain', 'text/csv', 'application/json', 'application/xml'],
        'archive': ['application/zip', 'application/x-rar-compressed', 'application/x-7z-compressed'],
        'code': ['text/x-python', 'text/javascript', 'text/html', 'text/css']
    }
    
    @staticmethod
    def validate_file(file: UploadFile) -> Tuple[bool, Optional[str]]:
        """
        Validate uploaded file
        
        Args:
            file: Uploaded file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check if file exists
            if not file.filename:
                return False, "No file provided"
            
            # Get file size
            file.file.seek(0, 2)  # Seek to end
            file_size = file.file.tell()
            file.file.seek(0)  # Reset to beginning
            
            # Check file size
            if file_size == 0:
                return False, "File is empty"
            
            # Detect MIME type
            mime_type = file.content_type or mimetypes.guess_type(file.filename)[0]
            if not mime_type:
                return False, "Unable to determine file type"
            
            # Check if file type is allowed
            if mime_type not in FileService.ALLOWED_FILE_TYPES:
                return False, f"File type '{mime_type}' is not allowed"
            
            # Check file size against limit for this type
            max_size = FileService.ALLOWED_FILE_TYPES[mime_type]
            if file_size > max_size:
                max_size_mb = max_size / (1024 * 1024)
                return False, f"File size ({file_size / (1024 * 1024):.1f}MB) exceeds limit ({max_size_mb:.1f}MB) for this file type"
            
            # Check filename for security
            if not FileService._is_safe_filename(file.filename):
                return False, "Filename contains invalid characters"
            
            return True, None
            
        except Exception as e:
            logger.error(f"File validation error: {str(e)}")
            return False, f"File validation failed: {str(e)}"
    
    @staticmethod
    def _is_safe_filename(filename: str) -> bool:
        """
        Check if filename is safe (no path traversal, etc.)
        
        Args:
            filename: Filename to check
            
        Returns:
            True if filename is safe
        """
        # Check for path traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            return False
        
        # Check for null bytes
        if '\x00' in filename:
            return False
        
        # Check for control characters
        if any(ord(char) < 32 for char in filename):
            return False
        
        # Check length
        if len(filename) > 255:
            return False
        
        return True
    
    @staticmethod
    async def save_file(
        file: UploadFile,
        project_id: int,
        user_id: int,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Save uploaded file to storage
        
        Args:
            file: Uploaded file
            project_id: Project ID
            user_id: Uploader user ID
            description: File description
            tags: File tags
            metadata: Additional metadata
            
        Returns:
            File information dictionary
        """
        try:
            # Validate file
            is_valid, error_msg = FileService.validate_file(file)
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_msg
                )
            
            # Generate unique filename
            file_extension = Path(file.filename).suffix.lower()
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            
            # Create storage directory structure
            storage_dir = FileService._get_storage_directory(project_id)
            storage_dir.mkdir(parents=True, exist_ok=True)
            
            # Full file path
            file_path = storage_dir / unique_filename
            
            # Save file to disk
            file_content = await file.read()
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            # Get file info
            file_size = len(file_content)
            mime_type = file.content_type or mimetypes.guess_type(file.filename)[0]
            
            # Prepare file information
            file_info = {
                'filename': unique_filename,
                'original_filename': file.filename,
                'file_size': file_size,
                'mime_type': mime_type,
                'file_path': str(file_path.relative_to(Path(settings.UPLOAD_DIR))),
                'project_id': project_id,
                'uploader_id': user_id,
                'upload_date': datetime.utcnow(),
                'description': description,
                'tags': tags or [],
                'metadata': metadata or {},
                'category': FileService._get_file_category(mime_type)
            }
            
            logger.info(f"File saved successfully: {file.filename} -> {unique_filename}")
            
            return file_info
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to save file: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save file: {str(e)}"
            )
    
    @staticmethod
    def _get_storage_directory(project_id: int) -> Path:
        """
        Get storage directory for project
        
        Args:
            project_id: Project ID
            
        Returns:
            Path to storage directory
        """
        base_dir = Path(settings.UPLOAD_DIR)
        return base_dir / "projects" / str(project_id) / "files"
    
    @staticmethod
    def _get_file_category(mime_type: str) -> str:
        """
        Get file category based on MIME type
        
        Args:
            mime_type: MIME type
            
        Returns:
            File category
        """
        for category, types in FileService.FILE_CATEGORIES.items():
            if mime_type in types:
                return category
        return 'other'
    
    @staticmethod
    async def delete_file(file_path: str) -> bool:
        """
        Delete file from storage
        
        Args:
            file_path: Relative path to file
            
        Returns:
            True if file deleted successfully
        """
        try:
            full_path = Path(settings.UPLOAD_DIR) / file_path
            if full_path.exists():
                full_path.unlink()
                logger.info(f"File deleted: {file_path}")
                return True
            else:
                logger.warning(f"File not found for deletion: {file_path}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {str(e)}")
            return False
    
    @staticmethod
    def get_file_url(file_path: str) -> str:
        """
        Get URL for accessing file
        
        Args:
            file_path: Relative path to file
            
        Returns:
            URL for file access
        """
        # In a real implementation, this would generate a proper URL
        # possibly with authentication/authorization tokens
        base_url = getattr(settings, 'FILE_BASE_URL', '/files')
        return f"{base_url}/{file_path}"
    
    @staticmethod
    def get_file_info(file_path: str) -> Optional[Dict[str, Any]]:
        """
        Get file information
        
        Args:
            file_path: Relative path to file
            
        Returns:
            File information dictionary or None if file not found
        """
        try:
            full_path = Path(settings.UPLOAD_DIR) / file_path
            if not full_path.exists():
                return None
            
            stat = full_path.stat()
            mime_type = mimetypes.guess_type(str(full_path))[0]
            
            return {
                'file_path': file_path,
                'file_size': stat.st_size,
                'mime_type': mime_type,
                'created_at': datetime.fromtimestamp(stat.st_ctime),
                'modified_at': datetime.fromtimestamp(stat.st_mtime),
                'category': FileService._get_file_category(mime_type or 'application/octet-stream')
            }
            
        except Exception as e:
            logger.error(f"Failed to get file info for {file_path}: {str(e)}")
            return None
    
    @staticmethod
    def generate_download_token(file_id: int, user_id: int, expires_in: int = 3600) -> str:
        """
        Generate temporary download token for file
        
        Args:
            file_id: File ID
            user_id: User ID requesting download
            expires_in: Token expiration time in seconds
            
        Returns:
            Download token
        """
        # In a real implementation, this would generate a JWT token
        # with file_id, user_id, and expiration time
        import secrets
        token = secrets.token_urlsafe(32)
        
        # Store token in cache/database with expiration
        logger.info(f"Generated download token for file {file_id}, user {user_id}")
        
        return token
    
    @staticmethod
    def validate_download_token(token: str, file_id: int, user_id: int) -> bool:
        """
        Validate download token
        
        Args:
            token: Download token
            file_id: File ID
            user_id: User ID
            
        Returns:
            True if token is valid
        """
        # In a real implementation, this would validate the JWT token
        # and check if it matches the file_id and user_id
        logger.info(f"Validating download token for file {file_id}, user {user_id}")
        
        # For now, always return True (placeholder implementation)
        return True