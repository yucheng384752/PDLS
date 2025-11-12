"""Base database models with common fields and functionality for PDLS"""

from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import Column, Integer, DateTime, Boolean, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import validates
from sqlalchemy.sql import func
import json

# Base class for all database models
Base = declarative_base()


class TimestampMixin:
    """Mixin for automatic timestamp management"""
    
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Record creation timestamp"
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Record last update timestamp"
    )


class SoftDeleteMixin:
    """Mixin for soft delete functionality"""
    
    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Record deletion timestamp (NULL means not deleted)"
    )
    
    is_deleted = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Soft delete flag"
    )
    
    def soft_delete(self):
        """Mark record as deleted without actually deleting it"""
        self.deleted_at = datetime.utcnow()
        self.is_deleted = True
    
    def restore(self):
        """Restore soft-deleted record"""
        self.deleted_at = None
        self.is_deleted = False


class AuditMixin:
    """Mixin for audit trail fields"""
    
    @declared_attr
    def created_by_id(cls):
        return Column(
            Integer,
            nullable=True,
            comment="ID of user who created this record"
        )
    
    @declared_attr
    def updated_by_id(cls):
        return Column(
            Integer, 
            nullable=True,
            comment="ID of user who last updated this record"
        )
    
    @declared_attr
    def deleted_by_id(cls):
        return Column(
            Integer,
            nullable=True,
            comment="ID of user who deleted this record"
        )


class MetadataMixin:
    """Mixin for storing additional metadata as JSON"""
    
    metadata_json = Column(
        Text,
        nullable=True,
        comment="Additional metadata stored as JSON"
    )
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """Get metadata as dictionary"""
        if self.metadata_json:
            try:
                return json.loads(self.metadata_json)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    @metadata.setter
    def metadata(self, value: Dict[str, Any]):
        """Set metadata from dictionary"""
        if value is None:
            self.metadata_json = None
        else:
            self.metadata_json = json.dumps(value, default=str)
    
    def update_metadata(self, updates: Dict[str, Any]):
        """Update specific metadata fields"""
        current_metadata = self.metadata
        current_metadata.update(updates)
        self.metadata = current_metadata
    
    def get_metadata_value(self, key: str, default: Any = None) -> Any:
        """Get specific metadata value"""
        return self.metadata.get(key, default)
    
    def set_metadata_value(self, key: str, value: Any):
        """Set specific metadata value"""
        current_metadata = self.metadata
        current_metadata[key] = value
        self.metadata = current_metadata


class BaseModel(Base, TimestampMixin, SoftDeleteMixin, AuditMixin, MetadataMixin):
    """
    Base model class with all common functionality
    
    Includes:
    - Primary key (id)
    - Timestamps (created_at, updated_at) 
    - Soft delete (deleted_at, is_deleted)
    - Audit trail (created_by_id, updated_by_id, deleted_by_id)
    - Metadata storage (metadata_json with property helpers)
    """
    
    __abstract__ = True
    
    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Primary key"
    )
    
    def __repr__(self) -> str:
        """String representation of model instance"""
        return f"<{self.__class__.__name__}(id={self.id})>"
    
    def to_dict(self, exclude: Optional[list] = None, include_metadata: bool = True) -> Dict[str, Any]:
        """
        Convert model instance to dictionary
        
        Args:
            exclude: List of fields to exclude from output
            include_metadata: Whether to include parsed metadata
            
        Returns:
            Dictionary representation of the model
        """
        exclude = exclude or []
        result = {}
        
        for column in self.__table__.columns:
            if column.name not in exclude:
                value = getattr(self, column.name)
                
                # Handle datetime serialization
                if isinstance(value, datetime):
                    result[column.name] = value.isoformat()
                else:
                    result[column.name] = value
        
        # Add parsed metadata if requested
        if include_metadata and 'metadata_json' not in exclude:
            result['metadata'] = self.metadata
            # Remove raw JSON field if metadata is included
            result.pop('metadata_json', None)
        
        return result
    
    def update_from_dict(self, data: Dict[str, Any], exclude: Optional[list] = None):
        """
        Update model instance from dictionary
        
        Args:
            data: Dictionary with field values
            exclude: List of fields to exclude from update
        """
        exclude = exclude or ['id', 'created_at', 'created_by_id']
        
        for key, value in data.items():
            if key not in exclude and hasattr(self, key):
                setattr(self, key, value)
    
    @validates('metadata_json')
    def validate_metadata_json(self, key, metadata_json):
        """Validate that metadata_json contains valid JSON"""
        if metadata_json is not None:
            try:
                json.loads(metadata_json)
            except (json.JSONDecodeError, TypeError):
                raise ValueError("metadata_json must contain valid JSON")
        return metadata_json


class NamedModel(BaseModel):
    """
    Base model for entities with name and description
    
    Extends BaseModel with common name/description fields
    """
    
    __abstract__ = True
    
    name = Column(
        String(255),
        nullable=False,
        comment="Entity name"
    )
    
    description = Column(
        Text,
        nullable=True,
        comment="Entity description"
    )
    
    def __repr__(self) -> str:
        """String representation including name"""
        return f"<{self.__class__.__name__}(id={self.id}, name='{self.name}')>"


class SlugMixin:
    """Mixin for URL-friendly slug field"""
    
    slug = Column(
        String(255),
        nullable=False,
        comment="URL-friendly identifier"
    )
    
    @validates('slug')
    def validate_slug(self, key, slug):
        """Validate slug format (lowercase, alphanumeric with hyphens)"""
        import re
        if slug and not re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', slug):
            raise ValueError("Slug must be lowercase alphanumeric with hyphens")
        return slug


class OrderedModel(BaseModel):
    """
    Base model for entities that need ordering
    
    Includes display_order field for manual sorting
    """
    
    __abstract__ = True
    
    display_order = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Display order for sorting"
    )


class OwnedModel(BaseModel):
    """
    Base model for entities with ownership
    
    Includes owner_id field linking to user
    """
    
    __abstract__ = True
    
    @declared_attr
    def owner_id(cls):
        return Column(
            Integer,
            nullable=False,
            comment="ID of the user who owns this entity"
        )


class StatusMixin:
    """Mixin for entities with status field"""
    
    status = Column(
        String(50),
        nullable=False,
        default="active",
        comment="Entity status"
    )
    
    @validates('status')
    def validate_status(self, key, status):
        """Validate status value against allowed values"""
        # This will be overridden in specific models with their allowed statuses
        return status


class VersionedMixin:
    """Mixin for entities with version tracking"""
    
    version = Column(
        Integer,
        default=1,
        nullable=False,
        comment="Entity version number"
    )
    
    def increment_version(self):
        """Increment version number"""
        self.version = (self.version or 0) + 1


# Utility functions for common model operations
def get_or_create(session, model, defaults=None, **kwargs):
    """
    Get existing instance or create new one
    
    Args:
        session: Database session
        model: Model class
        defaults: Default values for new instance
        **kwargs: Filter criteria
        
    Returns:
        Tuple of (instance, created_flag)
    """
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance, False
    else:
        params = kwargs.copy()
        params.update(defaults or {})
        instance = model(**params)
        return instance, True


def bulk_create_or_update(session, model, data_list, update_fields=None):
    """
    Bulk create or update model instances
    
    Args:
        session: Database session
        model: Model class
        data_list: List of dictionaries with model data
        update_fields: Fields to update on conflict
        
    Returns:
        List of model instances
    """
    instances = []
    for data in data_list:
        instance = model(**data)
        session.merge(instance)
        instances.append(instance)
    
    return instances