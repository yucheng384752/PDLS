"""Redis-based rate limiting system for PDLS application"""

import time
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from redis.asyncio import Redis
from fastapi import Request, HTTPException, status
from enum import Enum

from .redis import get_redis_client, CacheKeys
from .config import settings

logger = logging.getLogger(__name__)


class RateLimitStrategy(str, Enum):
    """Rate limiting strategies"""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"


class RateLimitRule:
    """Rate limit rule definition"""
    
    def __init__(
        self,
        requests: int,
        period: int,  # seconds
        strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW,
        burst_requests: Optional[int] = None,
        burst_period: Optional[int] = None
    ):
        self.requests = requests
        self.period = period
        self.strategy = strategy
        self.burst_requests = burst_requests or requests * 2
        self.burst_period = burst_period or 60  # 1 minute burst window


# Pre-defined rate limit rules
DEFAULT_RULES = {
    # General API endpoints
    "default": RateLimitRule(100, 900),  # 100 requests per 15 minutes
    
    # Authentication endpoints (more restrictive)
    "auth_login": RateLimitRule(5, 300, burst_requests=10),  # 5 per 5 min, burst 10/min
    "auth_register": RateLimitRule(3, 3600),  # 3 per hour
    "auth_reset_password": RateLimitRule(3, 3600),  # 3 per hour
    
    # File upload (bandwidth intensive)
    "file_upload": RateLimitRule(10, 300),  # 10 uploads per 5 minutes
    
    # Search endpoints (CPU intensive)
    "search": RateLimitRule(30, 60),  # 30 searches per minute
    
    # Admin endpoints
    "admin": RateLimitRule(200, 900),  # Higher limits for admins
    
    # Public endpoints (read-only)
    "public": RateLimitRule(300, 900),  # Higher limits for read operations
}


class RedisRateLimiter:
    """Redis-based rate limiter with multiple strategies"""
    
    def __init__(self, redis_client: Optional[Redis] = None):
        self.redis = redis_client or get_redis_client()
    
    async def is_allowed(
        self,
        key: str,
        rule: RateLimitRule,
        identifier: str = "default"
    ) -> Tuple[bool, Dict[str, int]]:
        """
        Check if request is allowed under rate limit
        
        Args:
            key: Rate limit key (usually includes IP/user ID)
            rule: Rate limit rule to apply
            identifier: Human-readable identifier for logging
            
        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        try:
            if rule.strategy == RateLimitStrategy.SLIDING_WINDOW:
                return await self._sliding_window_check(key, rule)
            elif rule.strategy == RateLimitStrategy.FIXED_WINDOW:
                return await self._fixed_window_check(key, rule)
            elif rule.strategy == RateLimitStrategy.TOKEN_BUCKET:
                return await self._token_bucket_check(key, rule)
            else:
                logger.error(f"Unknown rate limit strategy: {rule.strategy}")
                return True, {}
                
        except Exception as e:
            logger.error(f"Rate limit check failed for key '{key}': {e}")
            # Fail open - allow request if rate limiter fails
            return True, {}
    
    async def _sliding_window_check(
        self,
        key: str,
        rule: RateLimitRule
    ) -> Tuple[bool, Dict[str, int]]:
        """Sliding window rate limiting implementation"""
        current_time = int(time.time())
        window_start = current_time - rule.period
        
        pipe = self.redis.pipeline()
        
        # Remove expired entries
        pipe.zremrangebyscore(key, 0, window_start)
        
        # Count current requests in window
        pipe.zcard(key)
        
        # Add current request
        pipe.zadd(key, {str(current_time): current_time})
        
        # Set expiration
        pipe.expire(key, rule.period + 1)
        
        results = await pipe.execute()
        current_count = results[1]
        
        rate_limit_info = {
            "limit": rule.requests,
            "remaining": max(0, rule.requests - current_count - 1),
            "reset": current_time + rule.period,
            "retry_after": rule.period if current_count >= rule.requests else 0
        }
        
        is_allowed = current_count < rule.requests
        
        if not is_allowed:
            logger.warning(f"Rate limit exceeded for key '{key}': {current_count}/{rule.requests}")
        
        return is_allowed, rate_limit_info
    
    async def _fixed_window_check(
        self,
        key: str,
        rule: RateLimitRule
    ) -> Tuple[bool, Dict[str, int]]:
        """Fixed window rate limiting implementation"""
        current_time = int(time.time())
        window = current_time // rule.period
        window_key = f"{key}:window:{window}"
        
        pipe = self.redis.pipeline()
        
        # Increment counter for current window
        pipe.incr(window_key)
        pipe.expire(window_key, rule.period)
        
        results = await pipe.execute()
        current_count = results[0]
        
        window_reset = (window + 1) * rule.period
        
        rate_limit_info = {
            "limit": rule.requests,
            "remaining": max(0, rule.requests - current_count),
            "reset": window_reset,
            "retry_after": window_reset - current_time if current_count > rule.requests else 0
        }
        
        is_allowed = current_count <= rule.requests
        
        if not is_allowed:
            logger.warning(f"Rate limit exceeded for key '{window_key}': {current_count}/{rule.requests}")
        
        return is_allowed, rate_limit_info
    
    async def _token_bucket_check(
        self,
        key: str,
        rule: RateLimitRule
    ) -> Tuple[bool, Dict[str, int]]:
        """Token bucket rate limiting implementation"""
        current_time = time.time()
        bucket_key = f"{key}:bucket"
        
        # Get current bucket state
        bucket_data = await self.redis.hmget(bucket_key, "tokens", "last_refill")
        
        tokens = float(bucket_data[0] or rule.requests)
        last_refill = float(bucket_data[1] or current_time)
        
        # Calculate tokens to add since last refill
        time_passed = current_time - last_refill
        tokens_to_add = time_passed * (rule.requests / rule.period)
        tokens = min(rule.requests, tokens + tokens_to_add)
        
        # Check if request can be served
        is_allowed = tokens >= 1.0
        
        if is_allowed:
            tokens -= 1.0
        
        # Update bucket state
        await self.redis.hmset(bucket_key, {
            "tokens": str(tokens),
            "last_refill": str(current_time)
        })
        await self.redis.expire(bucket_key, rule.period * 2)
        
        rate_limit_info = {
            "limit": rule.requests,
            "remaining": int(tokens),
            "reset": int(current_time + (rule.requests - tokens) * (rule.period / rule.requests)),
            "retry_after": int((1.0 - tokens) * (rule.period / rule.requests)) if not is_allowed else 0
        }
        
        if not is_allowed:
            logger.warning(f"Rate limit exceeded for token bucket '{bucket_key}': {tokens} tokens remaining")
        
        return is_allowed, rate_limit_info
    
    async def reset_limit(self, key: str) -> bool:
        """Reset rate limit for a specific key"""
        try:
            # Delete all related keys
            keys_to_delete = [key, f"{key}:*"]
            for pattern in keys_to_delete:
                keys = await self.redis.keys(pattern)
                if keys:
                    await self.redis.delete(*keys)
            
            logger.info(f"Rate limit reset for key: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset rate limit for key '{key}': {e}")
            return False
    
    async def get_limit_info(self, key: str, rule: RateLimitRule) -> Dict[str, int]:
        """Get current rate limit information without consuming quota"""
        if rule.strategy == RateLimitStrategy.SLIDING_WINDOW:
            current_time = int(time.time())
            window_start = current_time - rule.period
            
            # Count current requests in window
            current_count = await self.redis.zcount(key, window_start, current_time)
            
            return {
                "limit": rule.requests,
                "remaining": max(0, rule.requests - current_count),
                "reset": current_time + rule.period,
                "current": current_count
            }
        
        elif rule.strategy == RateLimitStrategy.TOKEN_BUCKET:
            bucket_key = f"{key}:bucket"
            bucket_data = await self.redis.hmget(bucket_key, "tokens", "last_refill")
            
            current_time = time.time()
            tokens = float(bucket_data[0] or rule.requests)
            last_refill = float(bucket_data[1] or current_time)
            
            # Calculate current tokens
            time_passed = current_time - last_refill
            tokens_to_add = time_passed * (rule.requests / rule.period)
            tokens = min(rule.requests, tokens + tokens_to_add)
            
            return {
                "limit": rule.requests,
                "remaining": int(tokens),
                "reset": int(current_time + (rule.requests - tokens) * (rule.period / rule.requests)),
                "current": int(rule.requests - tokens)
            }
        
        else:  # Fixed window
            current_time = int(time.time())
            window = current_time // rule.period
            window_key = f"{key}:window:{window}"
            
            current_count = await self.redis.get(window_key) or 0
            current_count = int(current_count)
            
            return {
                "limit": rule.requests,
                "remaining": max(0, rule.requests - current_count),
                "reset": (window + 1) * rule.period,
                "current": current_count
            }


# Global rate limiter instance
rate_limiter = RedisRateLimiter()


def get_rate_limit_key(request: Request, rule_name: str) -> str:
    """Generate rate limit key based on request and rule"""
    # Get client identifier (IP or user ID)
    client_id = None
    
    # Try to get user ID from JWT token first
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            from .auth import verify_token
            token = auth_header.split(" ")[1]
            payload = verify_token(token)
            if payload:
                client_id = f"user:{payload.get('sub')}"
        except Exception:
            pass
    
    # Fall back to IP address
    if not client_id:
        ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        if not ip:
            ip = request.headers.get("X-Real-IP", "")
        if not ip:
            ip = request.client.host if request.client else "unknown"
        client_id = f"ip:{ip}"
    
    # Include endpoint path for granular limiting
    endpoint = request.url.path
    method = request.method.lower()
    
    return f"rate_limit:{rule_name}:{client_id}:{method}:{endpoint}"


async def check_rate_limit(
    request: Request,
    rule_name: str = "default",
    custom_rule: Optional[RateLimitRule] = None
) -> Dict[str, int]:
    """
    Check rate limit for request and return limit info
    
    Args:
        request: FastAPI request object
        rule_name: Name of rate limit rule to apply
        custom_rule: Custom rate limit rule (overrides rule_name)
        
    Returns:
        Rate limit information dictionary
        
    Raises:
        HTTPException: If rate limit is exceeded
    """
    # Get rate limit rule
    rule = custom_rule or DEFAULT_RULES.get(rule_name, DEFAULT_RULES["default"])
    
    # Generate rate limit key
    key = get_rate_limit_key(request, rule_name)
    
    # Check rate limit
    is_allowed, limit_info = await rate_limiter.is_allowed(key, rule, rule_name)
    
    if not is_allowed:
        # Log rate limit violation
        logger.warning(
            f"Rate limit exceeded: {rule_name} | "
            f"Key: {key} | "
            f"Limit: {limit_info.get('limit')} | "
            f"Path: {request.url.path}"
        )
        
        # Raise HTTP 429 Too Many Requests
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "rule": rule_name,
                "limit": limit_info.get("limit"),
                "retry_after": limit_info.get("retry_after", 60)
            },
            headers={
                "Retry-After": str(limit_info.get("retry_after", 60)),
                "X-RateLimit-Limit": str(limit_info.get("limit", 0)),
                "X-RateLimit-Remaining": str(limit_info.get("remaining", 0)),
                "X-RateLimit-Reset": str(limit_info.get("reset", 0))
            }
        )
    
    return limit_info


def add_rate_limit_headers(response, limit_info: Dict[str, int]):
    """Add rate limit headers to response"""
    response.headers["X-RateLimit-Limit"] = str(limit_info.get("limit", 0))
    response.headers["X-RateLimit-Remaining"] = str(limit_info.get("remaining", 0))
    response.headers["X-RateLimit-Reset"] = str(limit_info.get("reset", 0))


# Rate limiting decorator for FastAPI endpoints
def rate_limit(rule_name: str = "default", custom_rule: Optional[RateLimitRule] = None):
    """
    Decorator for applying rate limiting to FastAPI endpoints
    
    Usage:
        @router.get("/api/data")
        @rate_limit("search")
        async def get_data(request: Request):
            return {"data": "response"}
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract request from arguments
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                # Look in keyword arguments
                request = kwargs.get('request')
            
            if request:
                limit_info = await check_rate_limit(request, rule_name, custom_rule)
                # Store limit info in request state for response headers
                request.state.rate_limit_info = limit_info
            
            return await func(*args, **kwargs)
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    
    return decorator