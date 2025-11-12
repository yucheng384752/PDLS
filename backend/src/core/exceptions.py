"""Exception handling and custom exceptions for PDLS"""

import logging
from typing import Any, Dict, Optional
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from redis.exceptions import RedisError
from minio.error import S3Error
import traceback

logger = logging.getLogger(__name__)


class PDLSException(Exception):
    """Base exception class for PDLS application"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "PDLS_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(PDLSException):
    """Authentication related errors"""
    
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="AUTH_ERROR",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )


class AuthorizationError(PDLSException):
    """Authorization related errors"""
    
    def __init__(self, message: str = "Insufficient permissions", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="AUTHZ_ERROR",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details
        )


class ValidationError(PDLSException):
    """Data validation errors"""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        if field:
            error_details["field"] = field
            
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=error_details
        )


class NotFoundError(PDLSException):
    """Resource not found errors"""
    
    def __init__(self, resource: str, identifier: Any = None, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        if identifier is not None:
            error_details["identifier"] = str(identifier)
            error_details["resource_type"] = resource
            
        message = f"{resource} not found"
        if identifier is not None:
            message += f" with identifier: {identifier}"
            
        super().__init__(
            message=message,
            error_code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=error_details
        )


class ConflictError(PDLSException):
    """Resource conflict errors"""
    
    def __init__(self, message: str, resource: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        if resource:
            error_details["resource_type"] = resource
            
        super().__init__(
            message=message,
            error_code="CONFLICT",
            status_code=status.HTTP_409_CONFLICT,
            details=error_details
        )


class BusinessLogicError(PDLSException):
    """Business logic violation errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="BUSINESS_LOGIC_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


class ExternalServiceError(PDLSException):
    """External service integration errors"""
    
    def __init__(self, service: str, message: str, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        error_details["service"] = service
        
        super().__init__(
            message=f"External service error ({service}): {message}",
            error_code="EXTERNAL_SERVICE_ERROR",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=error_details
        )


class DatabaseError(PDLSException):
    """Database operation errors"""
    
    def __init__(self, message: str, operation: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        if operation:
            error_details["operation"] = operation
            
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=error_details
        )


class FileStorageError(PDLSException):
    """File storage related errors"""
    
    def __init__(self, message: str, operation: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        if operation:
            error_details["operation"] = operation
            
        super().__init__(
            message=message,
            error_code="FILE_STORAGE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=error_details
        )


class RateLimitError(PDLSException):
    """Rate limiting errors"""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        details = {}
        if retry_after:
            details["retry_after"] = retry_after
            
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details
        )


# Exception handlers for FastAPI
async def pdls_exception_handler(request: Request, exc: PDLSException) -> JSONResponse:
    """Handle custom PDLS exceptions"""
    logger.error(
        f"PDLS Exception: {exc.error_code} - {exc.message} | "
        f"Path: {request.url.path} | Details: {exc.details}"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle FastAPI validation errors"""
    logger.warning(f"Validation error on {request.url.path}: {exc.errors()}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Input validation failed",
                "details": {
                    "errors": exc.errors()
                }
            }
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions"""
    logger.warning(f"HTTP Exception {exc.status_code} on {request.url.path}: {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "HTTP_ERROR",
                "message": exc.detail,
                "details": {}
            }
        }
    )


async def database_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handle database exceptions"""
    error_message = "Database operation failed"
    error_code = "DATABASE_ERROR"
    
    if isinstance(exc, IntegrityError):
        error_message = "Data integrity constraint violation"
        error_code = "INTEGRITY_ERROR"
        status_code = status.HTTP_409_CONFLICT
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    
    logger.error(f"Database error on {request.url.path}: {str(exc)}")
    
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": error_code,
                "message": error_message,
                "details": {}
            }
        }
    )


async def redis_exception_handler(request: Request, exc: RedisError) -> JSONResponse:
    """Handle Redis exceptions"""
    logger.error(f"Redis error on {request.url.path}: {str(exc)}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "CACHE_ERROR",
                "message": "Cache operation failed",
                "details": {}
            }
        }
    )


async def minio_exception_handler(request: Request, exc: S3Error) -> JSONResponse:
    """Handle MinIO/S3 exceptions"""
    logger.error(f"MinIO error on {request.url.path}: {str(exc)}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "FILE_STORAGE_ERROR",
                "message": "File storage operation failed",
                "details": {}
            }
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all other exceptions"""
    logger.error(
        f"Unhandled exception on {request.url.path}: {str(exc)}\n"
        f"Traceback: {traceback.format_exc()}"
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": {}
            }
        }
    )


def register_exception_handlers(app):
    """Register all exception handlers with FastAPI app"""
    from fastapi.exceptions import RequestValidationError
    from sqlalchemy.exc import SQLAlchemyError
    from redis.exceptions import RedisError
    from minio.error import S3Error
    
    # Custom PDLS exceptions
    app.add_exception_handler(PDLSException, pdls_exception_handler)
    
    # FastAPI built-in exceptions
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    
    # Third-party exceptions
    app.add_exception_handler(SQLAlchemyError, database_exception_handler)
    app.add_exception_handler(RedisError, redis_exception_handler)
    app.add_exception_handler(S3Error, minio_exception_handler)
    
    # Catch-all for unhandled exceptions
    app.add_exception_handler(Exception, general_exception_handler)


# Utility functions for raising common errors
def raise_not_found(resource: str, identifier: Any = None) -> None:
    """Raise NotFoundError for a resource"""
    raise NotFoundError(resource, identifier)


def raise_validation_error(message: str, field: Optional[str] = None) -> None:
    """Raise ValidationError with message and optional field"""
    raise ValidationError(message, field)


def raise_permission_denied(message: str = "Insufficient permissions") -> None:
    """Raise AuthorizationError for permission denied"""
    raise AuthorizationError(message)


def raise_conflict(message: str, resource: Optional[str] = None) -> None:
    """Raise ConflictError for resource conflicts"""
    raise ConflictError(message, resource)


def handle_database_error(exc: Exception, operation: str) -> None:
    """Convert database exception to appropriate PDLS exception"""
    if isinstance(exc, IntegrityError):
        raise ConflictError("Data integrity constraint violation", details={"operation": operation})
    else:
        raise DatabaseError(f"Database operation failed: {str(exc)}", operation)