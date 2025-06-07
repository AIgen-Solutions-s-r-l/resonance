"""
Redis cache implementation.

This module provides a Redis-based implementation of the cache interface
with automatic serialization, TTL management, and error handling.
"""

import asyncio
import random
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from app.log.logging import logger

from app.libs.redis.connection import RedisConnectionManager
from app.libs.redis.serialization import RedisSerializer
from app.libs.redis.errors import (
    RedisCircuitBreakerOpenError,
    RedisConnectionError,
    RedisSerializationError
)


class RedisCache:
    """
    Redis-based cache implementation.
    
    This class provides a Redis-backed cache with automatic serialization,
    TTL management, connection error handling, and retry capabilities.
    """
    
    def __init__(
        self,
        connection_manager: RedisConnectionManager,
        ttl: int = 300,
        max_retries: int = 3,
        initial_backoff_ms: int = 100,
        max_backoff_ms: int = 30000,
        namespace: Optional[str] = None
    ):
        """
        Initialize Redis cache.
        
        Args:
            connection_manager: Redis connection manager
            ttl: Cache TTL in seconds
            max_retries: Maximum number of retry attempts
            initial_backoff_ms: Initial backoff in milliseconds
            max_backoff_ms: Maximum backoff in milliseconds
            namespace: Optional namespace prefix for cache keys
        """
        self._connection_manager = connection_manager
        self._ttl = ttl
        self._max_retries = max_retries
        self._initial_backoff_ms = initial_backoff_ms
        self._max_backoff_ms = max_backoff_ms
        self._namespace = namespace
        
        logger.info(
            f"Initialized Redis cache with TTL={ttl}s, "
            f"max_retries={max_retries}, "
            f"namespace={namespace or 'None'}"
        )
    
    def _add_namespace(self, key: str) -> str:
        """Add namespace prefix to key if namespace is set."""
        if self._namespace:
            return f"{self._namespace}:{key}"
        return key
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached results if available and not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached results or None if not found or expired
        """
        namespaced_key = self._add_namespace(key)
        start_time = time.time()
        retry_count = 0
        backoff_ms = self._initial_backoff_ms
        
        while retry_count <= self._max_retries:
            try:
                # Get Redis client
                redis = await self._connection_manager.get_redis()
                
                # Get data from Redis
                data = await redis.get(namespaced_key)
                
                if data:
                    # Deserialize data
                    try:
                        results = RedisSerializer.deserialize(data)
                        logger.debug(f"Cache hit for key: {key}")
                        elapsed = time.time() - start_time
                        logger.debug(f"Cache retrieval took {elapsed:.6f}s")
                        return results
                    except RedisSerializationError as e:
                        logger.error(f"Failed to deserialize cache data for key {key}: {str(e)}")
                        # Delete corrupted data
                        await redis.delete(namespaced_key)
                        return None
                
                logger.debug(f"Cache miss for key: {key}")
                return None
                
            except RedisCircuitBreakerOpenError:
                # Circuit breaker is open, don't retry
                logger.warning(f"Circuit breaker open, skipping cache get for key: {key}")
                return None
                
            except (RedisConnectionError, Exception) as e:
                retry_count += 1
                
                if retry_count > self._max_retries:
                    logger.error(f"Failed to get cache entry after {retry_count} retries: {str(e)}")
                    return None
                
                if isinstance(e, ValueError):
                    # then either redis disconnected or the client ended in an invalid state
                    await self._connection_manager._try_reconnect()
                
                # Calculate backoff with jitter
                jitter = random.uniform(0.8, 1.2)
                sleep_time = (backoff_ms / 1000.0) * jitter
                
                logger.warning(
                    f"Redis get error (attempt {retry_count}/{self._max_retries}), "
                    f"retrying in {sleep_time:.2f}s: {str(e)}"
                )
                
                await asyncio.sleep(sleep_time)
                
                # Exponential backoff with cap
                backoff_ms = min(backoff_ms * 2, self._max_backoff_ms)
        
        return None
        
    async def set(self, key: str, results: Dict[str, Any]) -> bool:
        """
        Store results in cache.
        
        Args:
            key: Cache key
            results: Results to cache
            
        Returns:
            True if stored successfully, False otherwise
        """
        namespaced_key = self._add_namespace(key)
        start_time = time.time()
        retry_count = 0
        backoff_ms = self._initial_backoff_ms
        
        # Serialize data
        try:
            data = RedisSerializer.serialize(results)
        except RedisSerializationError as e:
            logger.error(f"Failed to serialize cache data for key {key}: {str(e)}")
            return False
        
        while retry_count <= self._max_retries:
            try:
                # Get Redis client
                redis = await self._connection_manager.get_redis()
                
                # Store data in Redis with TTL
                await redis.setex(namespaced_key, self._ttl, data)
                
                logger.debug(f"Stored results in cache with key: {key}")
                elapsed = time.time() - start_time
                logger.debug(f"Cache storage took {elapsed:.6f}s")
                return True
                
            except RedisCircuitBreakerOpenError:
                # Circuit breaker is open, don't retry
                logger.warning(f"Circuit breaker open, skipping cache set for key: {key}")
                return False
                
            except (RedisConnectionError, Exception) as e:
                retry_count += 1
                
                if retry_count > self._max_retries:
                    logger.error(f"Failed to store cache entry after {retry_count} retries: {str(e)}")
                    return False
                
                # Calculate backoff with jitter
                jitter = random.uniform(0.8, 1.2)
                sleep_time = (backoff_ms / 1000.0) * jitter
                
                logger.warning(
                    f"Redis set error (attempt {retry_count}/{self._max_retries}), "
                    f"retrying in {sleep_time:.2f}s: {str(e)}"
                )
                
                await asyncio.sleep(sleep_time)
                
                # Exponential backoff with cap
                backoff_ms = min(backoff_ms * 2, self._max_backoff_ms)
        
        return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete a cache entry.
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted or not found, False on error
        """
        namespaced_key = self._add_namespace(key)
        
        try:
            # Get Redis client
            redis = await self._connection_manager.get_redis()
            
            # Delete key
            await redis.delete(namespaced_key)
            logger.debug(f"Deleted cache entry for key: {key}")
            return True
            
        except RedisCircuitBreakerOpenError:
            logger.warning(f"Circuit breaker open, skipping cache delete for key: {key}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete cache entry for key {key}: {str(e)}")
            return False
    
    async def generate_key(self, *args, **kwargs) -> str:
        """
        Generate a cache key from arguments.
        
        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Cache key string
        """
        key_parts = []
        
        # Add positional args
        for arg in args:
            if arg is not None:
                key_parts.append(str(arg))
        
        # Add keyword args
        for k, v in sorted(kwargs.items()):
            if v is not None:
                if isinstance(v, list):
                    v = sorted(v)
                key_parts.append(f"{k}_{v}")
        
        key = "_".join(str(part) for part in key_parts)
        logger.debug(f"Generated cache key: {key}")
        return key
    
    async def clear_namespace(self) -> bool:
        """
        Clear all keys in the current namespace.
        
        Returns:
            True if successful, False otherwise
        """
        if not self._namespace:
            logger.warning("Cannot clear namespace: no namespace set")
            return False
            
        try:
            # Get Redis client
            redis = await self._connection_manager.get_redis()
            
            # Find all keys in namespace
            pattern = f"{self._namespace}:*"
            cursor = 0
            count = 0
            
            # Scan keys in batches to avoid blocking Redis
            while True:
                cursor, keys = await redis.scan(cursor, match=pattern, count=100)
                
                if keys:
                    # Delete keys in this batch
                    await redis.delete(*keys)
                    count += len(keys)
                
                # If cursor is 0, we've processed all keys
                if cursor == 0:
                    break
            
            logger.info(f"Cleared {count} keys from namespace {self._namespace}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear namespace {self._namespace}: {str(e)}")
            return False