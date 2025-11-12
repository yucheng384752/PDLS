"""Base API response schemas and common data structures for PDLS"""

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


# Generic type for data payload
DataT = TypeVar('DataT')


class ResponseStatus(str, Enum):
    """Standard response status values"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    PARTIAL = "partial"


class BaseResponse(BaseModel, Generic[DataT]):
    """
    Base API response schema with consistent structure
    
    All API endpoints should return responses following this structure
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Operation completed successfully",
                "data": {},
                "meta": {
                    "timestamp": "2024-01-01T12:00:00Z",
                    "request_id": "12345-abcde",
                    "version": "1.0.0"
                }
            }
        }
    )
    
    status: ResponseStatus = Field(
        ...,
        description="Response status indicating success or failure"
    )
    
    message: str = Field(
        ...,
        description="Human-readable message describing the response"
    )
    
    data: Optional[DataT] = Field(
        None,
        description="Response payload data"
    )
    
    meta: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata about the response"
    )


class ErrorDetail(BaseModel):
    """Detailed error information"""
    
    code: str = Field(
        ...,
        description="Machine-readable error code"
    )
    
    message: str = Field(
        ...,
        description="Human-readable error message"
    )
    
    field: Optional[str] = Field(
        None,
        description="Field name if error is field-specific"
    )
    
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error details"
    )


class ErrorResponse(BaseModel):
    """Error response schema for API errors"""
    
    status: ResponseStatus = Field(
        ResponseStatus.ERROR,
        description="Response status (always 'error' for error responses)"
    )
    
    message: str = Field(
        ...,
        description="Human-readable error message"
    )
    
    error: ErrorDetail = Field(
        ...,
        description="Detailed error information"
    )
    
    meta: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata about the error"
    )


class PaginationMeta(BaseModel):
    """Pagination metadata for list responses"""
    
    page: int = Field(
        ...,
        ge=1,
        description="Current page number (1-based)"
    )
    
    page_size: int = Field(
        ...,
        ge=1,
        le=100,
        description="Number of items per page"
    )
    
    total_items: int = Field(
        ...,
        ge=0,
        description="Total number of items across all pages"
    )
    
    total_pages: int = Field(
        ...,
        ge=0,
        description="Total number of pages"
    )
    
    has_next: bool = Field(
        ...,
        description="Whether there is a next page"
    )
    
    has_prev: bool = Field(
        ...,
        description="Whether there is a previous page"
    )


class PaginatedResponse(BaseModel, Generic[DataT]):
    """Paginated response schema for list endpoints"""
    
    status: ResponseStatus = Field(
        ResponseStatus.SUCCESS,
        description="Response status"
    )
    
    message: str = Field(
        "Items retrieved successfully",
        description="Human-readable message"
    )
    
    data: List[DataT] = Field(
        ...,
        description="List of data items"
    )
    
    pagination: PaginationMeta = Field(
        ...,
        description="Pagination metadata"
    )
    
    meta: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata"
    )


class SuccessResponse(BaseResponse[DataT]):
    """Success response with predefined status"""
    
    status: ResponseStatus = Field(
        ResponseStatus.SUCCESS,
        description="Response status (always 'success')"
    )


class CreatedResponse(BaseResponse[DataT]):
    """Response for resource creation (HTTP 201)"""
    
    status: ResponseStatus = Field(
        ResponseStatus.SUCCESS,
        description="Response status"
    )
    
    message: str = Field(
        "Resource created successfully",
        description="Success message"
    )


class UpdatedResponse(BaseResponse[DataT]):
    """Response for resource updates (HTTP 200)"""
    
    status: ResponseStatus = Field(
        ResponseStatus.SUCCESS,
        description="Response status"
    )
    
    message: str = Field(
        "Resource updated successfully",
        description="Success message"
    )


class DeletedResponse(BaseModel):
    """Response for resource deletion (HTTP 204 or 200)"""
    
    status: ResponseStatus = Field(
        ResponseStatus.SUCCESS,
        description="Response status"
    )
    
    message: str = Field(
        "Resource deleted successfully",
        description="Success message"
    )
    
    meta: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata"
    )


class HealthResponse(BaseModel):
    """Health check response schema"""
    
    status: ResponseStatus = Field(
        ...,
        description="Overall health status"
    )
    
    message: str = Field(
        ...,
        description="Health status message"
    )
    
    services: Dict[str, Dict[str, Any]] = Field(
        ...,
        description="Individual service health statuses"
    )
    
    timestamp: datetime = Field(
        ...,
        description="Health check timestamp"
    )


# Base schemas for common entity operations
class BaseEntitySchema(BaseModel):
    """Base schema for entities with common fields"""
    
    id: int = Field(
        ...,
        description="Unique identifier"
    )
    
    created_at: datetime = Field(
        ...,
        description="Creation timestamp"
    )
    
    updated_at: datetime = Field(
        ...,
        description="Last update timestamp"
    )


class BaseCreateSchema(BaseModel):
    """Base schema for entity creation requests"""
    model_config = ConfigDict(extra='forbid')


class BaseUpdateSchema(BaseModel):
    """Base schema for entity update requests"""
    model_config = ConfigDict(extra='forbid')


class BaseQuerySchema(BaseModel):
    """Base schema for query parameters"""
    
    page: int = Field(
        1,
        ge=1,
        description="Page number for pagination"
    )
    
    page_size: int = Field(
        20,
        ge=1,
        le=100,
        description="Number of items per page"
    )
    
    sort_by: Optional[str] = Field(
        None,
        description="Field to sort by"
    )
    
    sort_order: Optional[str] = Field(
        "asc",
        pattern="^(asc|desc)$",
        description="Sort order: 'asc' or 'desc'"
    )
    
    search: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="Search query string"
    )


class FileUploadResponse(BaseModel):
    """Response schema for file upload operations"""
    
    file_id: str = Field(
        ...,
        description="Unique file identifier"
    )
    
    filename: str = Field(
        ...,
        description="Original filename"
    )
    
    file_size: int = Field(
        ...,
        description="File size in bytes"
    )
    
    content_type: str = Field(
        ...,
        description="MIME type of the file"
    )
    
    download_url: Optional[str] = Field(
        None,
        description="Temporary download URL"
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional file metadata"
    )


class BulkOperationResponse(BaseModel):
    """Response schema for bulk operations"""
    
    status: ResponseStatus = Field(
        ...,
        description="Overall operation status"
    )
    
    message: str = Field(
        ...,
        description="Operation summary message"
    )
    
    total_count: int = Field(
        ...,
        description="Total number of items processed"
    )
    
    success_count: int = Field(
        ...,
        description="Number of successfully processed items"
    )
    
    error_count: int = Field(
        ...,
        description="Number of items that failed processing"
    )
    
    errors: Optional[List[ErrorDetail]] = Field(
        None,
        description="List of errors for failed items"
    )
    
    results: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Results for successfully processed items"
    )


class ValidationErrorDetail(BaseModel):
    """Detailed validation error information"""
    
    field: str = Field(
        ...,
        description="Field name that failed validation"
    )
    
    message: str = Field(
        ...,
        description="Validation error message"
    )
    
    rejected_value: Any = Field(
        None,
        description="The value that was rejected"
    )
    
    constraint: Optional[str] = Field(
        None,
        description="Constraint that was violated"
    )


class ValidationErrorResponse(ErrorResponse):
    """Specialized error response for validation errors"""
    
    error: ErrorDetail = Field(
        ...,
        description="Validation error details"
    )
    
    validation_errors: List[ValidationErrorDetail] = Field(
        ...,
        description="List of field validation errors"
    )


# Utility functions for creating standardized responses
def create_success_response(
    data: Any = None,
    message: str = "Operation completed successfully",
    meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a standardized success response"""
    return {
        "status": ResponseStatus.SUCCESS,
        "message": message,
        "data": data,
        "meta": meta or {}
    }


def create_error_response(
    message: str,
    error_code: str,
    details: Optional[Dict[str, Any]] = None,
    meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a standardized error response"""
    return {
        "status": ResponseStatus.ERROR,
        "message": message,
        "error": {
            "code": error_code,
            "message": message,
            "details": details or {}
        },
        "meta": meta or {}
    }


def create_paginated_response(
    items: List[Any],
    page: int,
    page_size: int,
    total_items: int,
    message: str = "Items retrieved successfully",
    meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a standardized paginated response"""
    import math
    
    total_pages = math.ceil(total_items / page_size) if total_items > 0 else 0
    
    return {
        "status": ResponseStatus.SUCCESS,
        "message": message,
        "data": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        },
        "meta": meta or {}
    }