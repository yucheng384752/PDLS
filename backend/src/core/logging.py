"""Logging configuration for PDLS application"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

from .config import settings


def setup_logging(log_file: Optional[str] = None) -> None:
    """
    Configure application logging
    
    Args:
        log_file: Optional log file path. If None, uses default location.
    """
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Default log file with timestamp
    if log_file is None:
        timestamp = datetime.now().strftime("%Y%m%d")
        log_file = log_dir / f"pdls_{timestamp}.log"
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        fmt=settings.LOG_FORMAT,
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)  # Always log debug to file
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Configure third-party loggers
    configure_third_party_loggers()
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured - Level: {settings.LOG_LEVEL}, File: {log_file}")


def configure_third_party_loggers():
    """Configure logging levels for third-party libraries"""
    
    # Database and ORM
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("alembic").setLevel(logging.INFO)
    
    # HTTP and networking
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    # FastAPI and dependencies
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    
    # Redis
    logging.getLogger("redis").setLevel(logging.WARNING)
    
    # MinIO/S3
    logging.getLogger("minio").setLevel(logging.WARNING)
    logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
    
    # Celery (task queue)
    logging.getLogger("celery").setLevel(logging.INFO)
    logging.getLogger("celery.worker").setLevel(logging.INFO)
    logging.getLogger("celery.task").setLevel(logging.INFO)
    
    # Security libraries
    logging.getLogger("passlib").setLevel(logging.WARNING)
    logging.getLogger("jose").setLevel(logging.WARNING)


class SecurityFilter(logging.Filter):
    """Filter to remove sensitive information from logs"""
    
    SENSITIVE_FIELDS = [
        "password", "token", "secret", "key", "authorization",
        "cookie", "session", "csrf", "api_key", "access_key"
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter log record to remove sensitive data"""
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            # Check if any sensitive fields are in the message
            msg_lower = record.msg.lower()
            for field in self.SENSITIVE_FIELDS:
                if field in msg_lower:
                    # Replace sensitive information with placeholder
                    record.msg = self._sanitize_message(record.msg)
                    break
        
        return True
    
    def _sanitize_message(self, message: str) -> str:
        """Replace sensitive information in log message"""
        import re
        
        # Common patterns for sensitive data
        patterns = [
            (r'password["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', r'password: [REDACTED]'),
            (r'token["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', r'token: [REDACTED]'),
            (r'secret["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', r'secret: [REDACTED]'),
            (r'key["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', r'key: [REDACTED]'),
            (r'authorization["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', r'authorization: [REDACTED]'),
        ]
        
        sanitized = message
        for pattern, replacement in patterns:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        
        return sanitized


def get_logger(name: str) -> logging.Logger:
    """
    Get logger instance with security filter
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Add security filter if not already present
    if not any(isinstance(f, SecurityFilter) for f in logger.filters):
        logger.addFilter(SecurityFilter())
    
    return logger


def log_function_call(func_name: str, args: dict, user_id: Optional[int] = None):
    """
    Log function call for auditing purposes
    
    Args:
        func_name: Name of the function being called
        args: Function arguments (sensitive data will be filtered)
        user_id: ID of user making the call
    """
    logger = get_logger("pdls.audit")
    
    # Filter sensitive arguments
    filtered_args = {}
    for key, value in args.items():
        if any(sensitive in key.lower() for sensitive in SecurityFilter.SENSITIVE_FIELDS):
            filtered_args[key] = "[REDACTED]"
        else:
            filtered_args[key] = str(value)[:100]  # Limit length
    
    logger.info(
        f"Function call: {func_name} | User: {user_id or 'Anonymous'} | Args: {filtered_args}"
    )


def log_database_operation(
    operation: str,
    table: str,
    record_id: Optional[int] = None,
    user_id: Optional[int] = None,
    details: Optional[dict] = None
):
    """
    Log database operation for auditing
    
    Args:
        operation: Type of operation (INSERT, UPDATE, DELETE, SELECT)
        table: Database table name
        record_id: ID of affected record
        user_id: ID of user performing operation
        details: Additional operation details
    """
    logger = get_logger("pdls.database")
    
    logger.info(
        f"DB Operation: {operation} | Table: {table} | "
        f"Record: {record_id or 'N/A'} | User: {user_id or 'System'} | "
        f"Details: {details or {}}"
    )


def log_security_event(
    event_type: str,
    user_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    details: Optional[dict] = None,
    severity: str = "INFO"
):
    """
    Log security-related events
    
    Args:
        event_type: Type of security event
        user_id: ID of user involved
        ip_address: IP address of request
        details: Additional event details
        severity: Log severity level
    """
    logger = get_logger("pdls.security")
    
    log_level = getattr(logging, severity.upper(), logging.INFO)
    
    logger.log(
        log_level,
        f"Security Event: {event_type} | User: {user_id or 'Anonymous'} | "
        f"IP: {ip_address or 'Unknown'} | Details: {details or {}}"
    )


class ContextualLogger:
    """Logger that includes contextual information in all messages"""
    
    def __init__(self, name: str, context: dict):
        self.logger = get_logger(name)
        self.context = context
    
    def _add_context(self, message: str) -> str:
        """Add context information to log message"""
        context_str = " | ".join(f"{k}: {v}" for k, v in self.context.items())
        return f"{message} | Context: {context_str}"
    
    def debug(self, message: str, *args, **kwargs):
        self.logger.debug(self._add_context(message), *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        self.logger.info(self._add_context(message), *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        self.logger.warning(self._add_context(message), *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        self.logger.error(self._add_context(message), *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        self.logger.critical(self._add_context(message), *args, **kwargs)


def create_request_logger(request_id: str, user_id: Optional[int] = None) -> ContextualLogger:
    """
    Create logger with request context
    
    Args:
        request_id: Unique request identifier
        user_id: ID of user making the request
        
    Returns:
        Logger with request context
    """
    context = {
        "request_id": request_id,
        "user_id": user_id or "Anonymous",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    return ContextualLogger("pdls.request", context)