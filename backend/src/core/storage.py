"""MinIO storage client configuration for PDLS file management"""

import os
import logging
from typing import Optional, BinaryIO, Generator, Tuple
from datetime import datetime, timedelta
from urllib.parse import quote
from minio import Minio
from minio.error import S3Error
import uuid

from .config import settings

logger = logging.getLogger(__name__)

# Global MinIO client instance
minio_client: Optional[Minio] = None


def init_minio() -> Minio:
    """Initialize MinIO client"""
    global minio_client
    
    try:
        minio_client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_USE_SSL
        )
        
        # Test connection and ensure bucket exists
        if not minio_client.bucket_exists(settings.MINIO_BUCKET_NAME):
            minio_client.make_bucket(settings.MINIO_BUCKET_NAME)
            logger.info(f"Created MinIO bucket: {settings.MINIO_BUCKET_NAME}")
        
        logger.info("MinIO connection established successfully")
        return minio_client
        
    except Exception as e:
        logger.error(f"Failed to initialize MinIO client: {e}")
        raise


def get_minio_client() -> Minio:
    """Get MinIO client instance"""
    if minio_client is None:
        raise RuntimeError("MinIO client not initialized. Call init_minio() first.")
    return minio_client


class FileStorage:
    """MinIO file storage utility class"""
    
    def __init__(self, client: Optional[Minio] = None, bucket: Optional[str] = None):
        self.client = client or get_minio_client()
        self.bucket = bucket or settings.MINIO_BUCKET_NAME
    
    def generate_file_key(self, prefix: str, filename: str) -> str:
        """
        Generate unique file key with prefix
        
        Args:
            prefix: File type prefix (e.g., 'projects', 'logs', 'avatars')
            filename: Original filename
            
        Returns:
            Unique file key
        """
        # Extract file extension
        name, ext = os.path.splitext(filename)
        
        # Generate unique ID
        unique_id = str(uuid.uuid4())
        
        # Create safe filename
        safe_name = "".join(c if c.isalnum() or c in '.-_' else '_' for c in name)
        
        # Build key with timestamp for organization
        timestamp = datetime.utcnow().strftime("%Y/%m/%d")
        
        return f"{prefix}/{timestamp}/{unique_id}_{safe_name}{ext}"
    
    def upload_file(
        self,
        file_data: BinaryIO,
        file_key: str,
        content_type: str = "application/octet-stream",
        metadata: Optional[dict] = None
    ) -> bool:
        """
        Upload file to MinIO storage
        
        Args:
            file_data: File data stream
            file_key: Storage key/path for the file
            content_type: MIME type of the file
            metadata: Additional metadata to store with file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get file size
            file_data.seek(0, 2)  # Seek to end
            file_size = file_data.tell()
            file_data.seek(0)  # Reset to beginning
            
            # Upload file
            self.client.put_object(
                bucket_name=self.bucket,
                object_name=file_key,
                data=file_data,
                length=file_size,
                content_type=content_type,
                metadata=metadata or {}
            )
            
            logger.info(f"Successfully uploaded file: {file_key}")
            return True
            
        except S3Error as e:
            logger.error(f"MinIO error uploading file {file_key}: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to upload file {file_key}: {e}")
            return False
    
    def download_file(self, file_key: str) -> Optional[BinaryIO]:
        """
        Download file from MinIO storage
        
        Args:
            file_key: Storage key/path of the file
            
        Returns:
            File data stream or None if not found
        """
        try:
            response = self.client.get_object(self.bucket, file_key)
            return response
            
        except S3Error as e:
            if e.code == "NoSuchKey":
                logger.warning(f"File not found: {file_key}")
            else:
                logger.error(f"MinIO error downloading file {file_key}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to download file {file_key}: {e}")
            return None
    
    def delete_file(self, file_key: str) -> bool:
        """
        Delete file from MinIO storage
        
        Args:
            file_key: Storage key/path of the file
            
        Returns:
            True if successful or file not found, False on error
        """
        try:
            self.client.remove_object(self.bucket, file_key)
            logger.info(f"Successfully deleted file: {file_key}")
            return True
            
        except S3Error as e:
            if e.code == "NoSuchKey":
                logger.info(f"File already deleted or not found: {file_key}")
                return True
            logger.error(f"MinIO error deleting file {file_key}: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete file {file_key}: {e}")
            return False
    
    def get_file_info(self, file_key: str) -> Optional[dict]:
        """
        Get file information and metadata
        
        Args:
            file_key: Storage key/path of the file
            
        Returns:
            Dictionary with file info or None if not found
        """
        try:
            stat = self.client.stat_object(self.bucket, file_key)
            
            return {
                "size": stat.size,
                "last_modified": stat.last_modified,
                "etag": stat.etag,
                "content_type": stat.content_type,
                "metadata": stat.metadata,
                "version_id": stat.version_id
            }
            
        except S3Error as e:
            if e.code == "NoSuchKey":
                logger.warning(f"File not found: {file_key}")
            else:
                logger.error(f"MinIO error getting file info {file_key}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to get file info {file_key}: {e}")
            return None
    
    def generate_presigned_url(
        self,
        file_key: str,
        expires: timedelta = timedelta(hours=1),
        method: str = "GET"
    ) -> Optional[str]:
        """
        Generate presigned URL for file access
        
        Args:
            file_key: Storage key/path of the file
            expires: URL expiration time
            method: HTTP method (GET for download, PUT for upload)
            
        Returns:
            Presigned URL or None if failed
        """
        try:
            if method.upper() == "GET":
                url = self.client.presigned_get_object(
                    bucket_name=self.bucket,
                    object_name=file_key,
                    expires=expires
                )
            elif method.upper() == "PUT":
                url = self.client.presigned_put_object(
                    bucket_name=self.bucket,
                    object_name=file_key,
                    expires=expires
                )
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            return url
            
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for {file_key}: {e}")
            return None
    
    def list_files(
        self,
        prefix: str = "",
        max_keys: int = 1000
    ) -> Generator[Tuple[str, dict], None, None]:
        """
        List files with given prefix
        
        Args:
            prefix: File key prefix to filter by
            max_keys: Maximum number of files to return
            
        Yields:
            Tuples of (file_key, file_info)
        """
        try:
            count = 0
            for obj in self.client.list_objects(
                bucket_name=self.bucket,
                prefix=prefix,
                recursive=True
            ):
                if count >= max_keys:
                    break
                
                yield (obj.object_name, {
                    "size": obj.size,
                    "last_modified": obj.last_modified,
                    "etag": obj.etag,
                    "is_dir": obj.is_dir,
                    "version_id": obj.version_id
                })
                
                count += 1
                
        except Exception as e:
            logger.error(f"Failed to list files with prefix '{prefix}': {e}")
    
    def copy_file(self, source_key: str, dest_key: str) -> bool:
        """
        Copy file within storage
        
        Args:
            source_key: Source file key
            dest_key: Destination file key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from minio.commonconfig import CopySource
            
            copy_source = CopySource(self.bucket, source_key)
            self.client.copy_object(self.bucket, dest_key, copy_source)
            
            logger.info(f"Successfully copied file from {source_key} to {dest_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to copy file from {source_key} to {dest_key}: {e}")
            return False


# Global storage instance
file_storage = FileStorage()


class StoragePaths:
    """Storage path constants and generators"""
    
    # Path prefixes for different file types
    AVATARS = "avatars"
    PROJECT_FILES = "projects"
    LOG_ATTACHMENTS = "logs/attachments"
    LOG_IMAGES = "logs/images"
    DOCUMENTS = "documents"
    EXPORTS = "exports"
    TEMP = "temp"
    
    @staticmethod
    def avatar_path(user_id: int, filename: str) -> str:
        """Generate avatar file path"""
        return file_storage.generate_file_key(StoragePaths.AVATARS, f"user_{user_id}_{filename}")
    
    @staticmethod
    def project_file_path(project_id: int, filename: str) -> str:
        """Generate project file path"""
        return file_storage.generate_file_key(StoragePaths.PROJECT_FILES, f"project_{project_id}_{filename}")
    
    @staticmethod
    def log_attachment_path(log_id: int, filename: str) -> str:
        """Generate log attachment file path"""
        return file_storage.generate_file_key(StoragePaths.LOG_ATTACHMENTS, f"log_{log_id}_{filename}")
    
    @staticmethod
    def log_image_path(log_id: int, filename: str) -> str:
        """Generate log image file path"""
        return file_storage.generate_file_key(StoragePaths.LOG_IMAGES, f"log_{log_id}_{filename}")