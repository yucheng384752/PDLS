"""Middleware configuration for PDLS FastAPI application"""

import time
import uuid
from typing import Callable, Optional
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.sessions import SessionMiddleware
import logging

from ..core.config import settings
from ..core.logging import create_request_logger, log_security_event

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        # Create request logger
        request_logger = create_request_logger(request_id)
        
        # Log request start
        start_time = time.time()
        client_ip = self._get_client_ip(request)
        
        request_logger.info(
            f"Request started: {request.method} {request.url.path} | "
            f"IP: {client_ip} | User-Agent: {request.headers.get('user-agent', 'Unknown')}"
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log successful response
            request_logger.info(
                f"Request completed: {response.status_code} | "
                f"Time: {process_time:.3f}s | Size: {response.headers.get('content-length', 'Unknown')}"
            )
            
            # Add custom headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            # Calculate processing time for errors
            process_time = time.time() - start_time
            
            # Log error
            request_logger.error(
                f"Request failed: {str(e)} | Time: {process_time:.3f}s"
            )
            
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request"""
        # Check for forwarded IP in headers (behind proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct client IP
        return request.client.host if request.client else "unknown"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers to responses"""
    
    def __init__(self, app, csp_policy: Optional[str] = None):
        super().__init__(app)
        self.csp_policy = csp_policy or (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'"
        )
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Security headers
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": self.csp_policy,
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": (
                "geolocation=(), microphone=(), camera=(), "
                "payment=(), usb=(), magnetometer=(), gyroscope=()"
            ),
        }
        
        # Add security headers to response
        for header, value in security_headers.items():
            response.headers[header] = value
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-based rate limiting middleware"""
    
    def __init__(self, app, enable_rate_limiting: bool = True):
        super().__init__(app)
        self.enable_rate_limiting = enable_rate_limiting and not settings.DEBUG
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks, metrics, and static files
        if (not self.enable_rate_limiting or 
            request.url.path in ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"] or 
            request.url.path.startswith("/static")):
            return await call_next(request)
        
        try:
            # Determine rate limit rule based on endpoint
            rule_name = self._get_rate_limit_rule(request)
            
            # Check rate limit using Redis-based limiter
            from .rate_limit import check_rate_limit
            limit_info = await check_rate_limit(request, rule_name)
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers to response
            from .rate_limit import add_rate_limit_headers
            add_rate_limit_headers(response, limit_info)
            
            return response
            
        except Exception as e:
            # If rate limiting fails, log error and continue (fail-open)
            if "Rate limit exceeded" not in str(e):
                logger.error(f"Rate limiting middleware error: {e}")
            raise
    
    def _get_rate_limit_rule(self, request: Request) -> str:
        """Determine appropriate rate limit rule for the request"""
        path = request.url.path.lower()
        method = request.method.lower()
        
        # Authentication endpoints
        if "/auth/" in path:
            if "login" in path:
                return "auth_login"
            elif "register" in path:
                return "auth_register"
            elif "reset" in path or "password" in path:
                return "auth_reset_password"
            else:
                return "auth_login"  # Default for auth endpoints
        
        # File upload endpoints
        if "/files/" in path and method in ["post", "put"]:
            return "file_upload"
        
        # Search endpoints
        if "/search" in path or "query" in path:
            return "search"
        
        # Admin endpoints
        if "/admin/" in path:
            return "admin"
        
        # Public read-only endpoints
        if method == "get" and any(public_path in path for public_path in ["/public/", "/docs/", "/health"]):
            return "public"
        
        # Default rule for all other endpoints
        return "default"


class DatabaseHealthMiddleware(BaseHTTPMiddleware):
    """Middleware to check database health and add to response headers"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Add database health check for non-static requests
        if not request.url.path.startswith("/static"):
            try:
                # This would be implemented when database models are ready
                # For now, just indicate middleware is working
                db_status = "healthy"
            except Exception:
                db_status = "unhealthy"
                logger.error("Database health check failed")
            
            request.state.db_status = db_status
        
        response = await call_next(request)
        
        # Add database status to response headers for debugging
        if hasattr(request.state, 'db_status'):
            response.headers["X-Database-Status"] = request.state.db_status
        
        return response


def setup_middleware(app: FastAPI) -> None:
    """
    Configure all middleware for the FastAPI application
    
    Args:
        app: FastAPI application instance
    """
    # 1. Trusted Host Middleware (should be first)
    if not settings.DEBUG:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["localhost", "127.0.0.1", "*.yourdomain.com"]
        )
    
    # 2. CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time"]
    )
    
    # 3. Security Headers Middleware
    app.add_middleware(SecurityHeadersMiddleware)
    
    # 4. Rate Limiting Middleware
    app.add_middleware(
        RateLimitMiddleware,
        enable_rate_limiting=not settings.DEBUG
    )
    
    # 5. Request Logging Middleware
    app.add_middleware(RequestLoggingMiddleware)
    
    # 6. Database Health Middleware
    app.add_middleware(DatabaseHealthMiddleware)
    
    # 7. Session Middleware (for storing temporary data)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.SECRET_KEY,
        max_age=3600,  # 1 hour
        same_site="strict",
        https_only=not settings.DEBUG
    )
    
    # 8. GZip Middleware (should be last)
    app.add_middleware(
        GZipMiddleware,
        minimum_size=1000  # Only compress responses larger than 1KB
    )
    
    logger.info("All middleware configured successfully")


def get_request_id(request: Request) -> str:
    """
    Get request ID from request state
    
    Args:
        request: FastAPI request object
        
    Returns:
        Request ID string
    """
    return getattr(request.state, 'request_id', 'unknown')


def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request
    
    Args:
        request: FastAPI request object
        
    Returns:
        Client IP address
    """
    # Check for forwarded IP in headers (behind proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fall back to direct client IP
    return request.client.host if request.client else "unknown"