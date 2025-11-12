"""Redis client configuration and utilities for PDLS"""

import json
import logging
from typing import Any, Optional, Union
from datetime import timedelta
import redis.asyncio as redis
from redis.asyncio import Redis
from contextlib import asynccontextmanager

from .config import settings

logger = logging.getLogger(__name__)

# Global Redis client instance
redis_client: Optional[Redis] = None


async def init_redis() -> Redis:
    """Initialize Redis connection"""
    global redis_client
    
    try:
        redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_keepalive=True,
            socket_keepalive_options={},
            health_check_interval=30,
        )
        
        # Test connection
        await redis_client.ping()
        logger.info("Redis connection established successfully")
        
        return redis_client
        
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise


async def close_redis():
    """Close Redis connection"""
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None
        logger.info("Redis connection closed")


def get_redis_client() -> Redis:
    """Get Redis client instance"""
    if redis_client is None:
        raise RuntimeError("Redis client not initialized. Call init_redis() first.")
    return redis_client


class RedisCache:
    """Redis cache utility class with JSON serialization support"""
    
    def __init__(self, client: Optional[Redis] = None):
        self.client = client or get_redis_client()
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache with JSON deserialization
        
        Args:
            key: Cache key
            
        Returns:
            Deserialized value or None if not found
        """
        try:
            value = await self.client.get(key)
            if value is None:
                return None
            return json.loads(value)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to deserialize cache value for key '{key}': {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[Union[int, timedelta]] = None
    ) -> bool:
        """
        Set value in cache with JSON serialization
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            expire: Expiration time in seconds or timedelta
            
        Returns:
            True if successful, False otherwise
        """
        try:
            serialized_value = json.dumps(value, default=str)
            return await self.client.set(key, serialized_value, ex=expire)
        except Exception as e:
            logger.error(f"Failed to set cache value for key '{key}': {e}")
            return False
    
    async def delete(self, *keys: str) -> int:
        """
        Delete keys from cache
        
        Args:
            keys: Cache keys to delete
            
        Returns:
            Number of keys deleted
        """
        try:
            return await self.client.delete(*keys)
        except Exception as e:
            logger.error(f"Failed to delete cache keys {keys}: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists, False otherwise
        """
        try:
            return await self.client.exists(key) > 0
        except Exception as e:
            logger.error(f"Failed to check cache key existence '{key}': {e}")
            return False
    
    async def expire(self, key: str, time: Union[int, timedelta]) -> bool:
        """
        Set expiration time for a key
        
        Args:
            key: Cache key
            time: Expiration time in seconds or timedelta
            
        Returns:
            True if successful, False otherwise
        """
        try:
            return await self.client.expire(key, time)
        except Exception as e:
            logger.error(f"Failed to set expiration for key '{key}': {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Increment integer value in cache
        
        Args:
            key: Cache key
            amount: Amount to increment by
            
        Returns:
            New value after increment or None if failed
        """
        try:
            return await self.client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Failed to increment key '{key}': {e}")
            return None
    
    async def get_many(self, *keys: str) -> dict[str, Any]:
        """
        Get multiple values from cache
        
        Args:
            keys: Cache keys
            
        Returns:
            Dictionary mapping keys to their deserialized values
        """
        try:
            values = await self.client.mget(*keys)
            result = {}
            
            for key, value in zip(keys, values):
                if value is not None:
                    try:
                        result[key] = json.loads(value)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to deserialize value for key '{key}'")
                        result[key] = None
                else:
                    result[key] = None
                    
            return result
            
        except Exception as e:
            logger.error(f"Failed to get multiple cache keys {keys}: {e}")
            return {key: None for key in keys}
    
    async def set_many(
        self,
        mapping: dict[str, Any],
        expire: Optional[Union[int, timedelta]] = None
    ) -> bool:
        """
        Set multiple values in cache
        
        Args:
            mapping: Dictionary of key-value pairs
            expire: Expiration time for all keys
            
        Returns:
            True if all operations successful, False otherwise
        """
        try:
            # Serialize all values
            serialized_mapping = {}
            for key, value in mapping.items():
                serialized_mapping[key] = json.dumps(value, default=str)
            
            # Set all values
            result = await self.client.mset(serialized_mapping)
            
            # Set expiration if specified
            if expire and result:
                pipeline = self.client.pipeline()
                for key in mapping.keys():
                    pipeline.expire(key, expire)
                await pipeline.execute()
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to set multiple cache values: {e}")
            return False


# Global cache instance
cache = RedisCache()


class CacheKeys:
    """Cache key constants and generators"""
    
    # User session keys
    USER_SESSION = "user:session:{user_id}"
    USER_PERMISSIONS = "user:permissions:{user_id}"
    USER_ROLES = "user:roles:{user_id}"
    
    # Project cache keys
    PROJECT_DETAILS = "project:{project_id}"
    PROJECT_MEMBERS = "project:members:{project_id}"
    PROJECT_LOGS = "project:logs:{project_id}:page:{page}"
    
    # Development log keys
    DEV_LOG_DETAILS = "devlog:{log_id}"
    DEV_LOG_COMMENTS = "devlog:comments:{log_id}"
    
    # File cache keys
    FILE_METADATA = "file:metadata:{file_id}"
    FILE_ACCESS_TOKEN = "file:access:{token}"
    
    # Rate limiting keys
    RATE_LIMIT_USER = "rate_limit:user:{user_id}:{endpoint}"
    RATE_LIMIT_IP = "rate_limit:ip:{ip}:{endpoint}"
    
    # Task queue keys
    TASK_STATUS = "task:status:{task_id}"
    TASK_RESULT = "task:result:{task_id}"
    
    @staticmethod
    def user_session(user_id: int) -> str:
        return CacheKeys.USER_SESSION.format(user_id=user_id)
    
    @staticmethod
    def user_permissions(user_id: int) -> str:
        return CacheKeys.USER_PERMISSIONS.format(user_id=user_id)
    
    @staticmethod
    def project_details(project_id: int) -> str:
        return CacheKeys.PROJECT_DETAILS.format(project_id=project_id)
    
    @staticmethod
    def dev_log_details(log_id: int) -> str:
        return CacheKeys.DEV_LOG_DETAILS.format(log_id=log_id)