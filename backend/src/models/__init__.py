"""Database models for PDLS (Project Development Log System)"""

from .base import (
    Base,
    BaseModel,
    NamedModel,
    TimestampMixin,
    SoftDeleteMixin,
    AuditMixin,
    MetadataMixin,
    SlugMixin,
    OrderedModel,
    OwnedModel,
    StatusMixin,
    VersionedMixin,
    get_or_create,
    bulk_create_or_update
)

from .user import (
    User,
    UserRole,
    UserStatus
)

# Export all models and utilities
__all__ = [
    # Base classes and mixins
    'Base',
    'BaseModel', 
    'NamedModel',
    'TimestampMixin',
    'SoftDeleteMixin',
    'AuditMixin', 
    'MetadataMixin',
    'SlugMixin',
    'OrderedModel',
    'OwnedModel',
    'StatusMixin',
    'VersionedMixin',
    
    # User management
    'User',
    'UserRole',
    'UserStatus',
    
    # Utility functions
    'get_or_create',
    'bulk_create_or_update'
]