"""
Caching mechanism for job matcher.

This module provides caching functionality for job matching results, using
Redis for distributed caching with fallback to local memory cache when Redis
is unavailable.
"""

import asyncio
import warnings
from time import time
from typing import Dict, Any, Optional, Tuple, Union
from loguru import logger

# Import Redis cache implementation
from app.libs.redis.factory import RedisCacheFactory, initialize_cache as init_redis_cache
from app.libs.redis.monitoring import create_metrics_wrapped_cache
from app.libs.redis.errors import RedisCircuitBreakerOpenError, RedisConnectionError


class ResultsCache:
    """
    Cache for job matching results.
    
    Note:
        This in-memory implementation is maintained for backward compatibility
        and fallback purposes. The system will use Redis for caching when available.
    """
    
    def __init__(self, ttl: int = 300, max_size: int = 1000):
        """
        Initialize the cache.
        
        Args:
            ttl: Cache TTL in seconds
            max_size: Maximum number of entries in cache
        """
        warnings.warn(
            "In-memory ResultsCache is deprecated. Redis cache will be used when available.",
            DeprecationWarning,
            stacklevel=2
        )
        self._cache: Dict[str, Tuple[Dict[str, Any], float]] = {}
        self._ttl = ttl
        self._max_size = max_size
        self._lock = asyncio.Lock()
        logger.info(f"Initialized in-memory job matcher cache with TTL={ttl}s, max_size={max_size}")
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached results if available and not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached results or None if not found or expired
        """
        start_time = time()
        async with self._lock:
            if key in self._cache:
                results, timestamp = self._cache[key]
                # Check if cache entry has expired
                if time() - timestamp <= self._ttl:
                    logger.debug(f"Local cache hit for key: {key}")
                    elapsed = time() - start_time
                    logger.debug(f"Local cache retrieval took {elapsed:.6f}s")
                    return results
                
                # Cache entry has expired
                logger.debug(f"Local cache entry expired for key: {key}")
                del self._cache[key]
        
        logger.debug(f"Local cache miss for key: {key}")
        return None
    
    async def set(self, key: str, results: Dict[str, Any]) -> bool:
        """
        Store results in cache.
        
        Args:
            key: Cache key
            results: Results to cache
            
        Returns:
            True if stored successfully
        """
        start_time = time()
        async with self._lock:
            self._cache[key] = (results, time())
            logger.debug(f"Stored results in local cache with key: {key}")
            
            # Cleanup cache if it gets too large
            if len(self._cache) > self._max_size:
                logger.info(f"Local cache cleanup triggered (size={len(self._cache)})")
                # Remove oldest entries
                sorted_items = sorted(self._cache.items(), key=lambda x: x[1][1])
                to_remove = len(self._cache) // 2  # Remove half of the entries
                
                for k, _ in sorted_items[:to_remove]:
                    del self._cache[k]
                
                logger.info(f"Removed {to_remove} oldest local cache entries")
        
        elapsed = time() - start_time
        logger.debug(f"Local cache storage took {elapsed:.6f}s")
        return True
    
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
        logger.trace(f"Generated cache key: {key}")
        return key


# Hybrid cache that switches between Redis and in-memory cache
class HybridCache:
    """
    Hybrid cache implementation that uses Redis when available and falls back
    to in-memory cache when Redis is unavailable.
    """
    
    def __init__(self, ttl: int = 300, max_size: int = 1000):
        """
        Initialize the hybrid cache.
        
        Args:
            ttl: Cache TTL in seconds
            max_size: Maximum number of entries in local cache
        """
        self._redis_cache = None  # Will be set during initialization
        self._memory_cache = ResultsCache(ttl=ttl, max_size=max_size)
        self._initialized = False
        self._ttl = ttl
        logger.info(f"Initialized hybrid cache with TTL={ttl}s")
        
    async def initialize(self) -> None:
        """Initialize the Redis cache component."""
        if self._initialized:
            return
            
        try:
            # Initialize Redis cache
            redis_cache = await init_redis_cache()
            
            if redis_cache is not None:
                # Wrap with metrics monitoring if available
                self._redis_cache = create_metrics_wrapped_cache(redis_cache)
                logger.info("Hybrid cache initialized with Redis")
            else:
                logger.warning(
                    "Redis cache initialization failed, falling back to in-memory cache only"
                )
        except Exception as e:
            logger.exception(f"Error initializing Redis cache: {str(e)}")
        
        self._initialized = True
        
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached results if available and not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached results or None if not found or expired
        """
        # Ensure cache is initialized
        if not self._initialized:
            await self.initialize()
        
        # Try Redis first if available
        if self._redis_cache is not None:
            try:
                result = await self._redis_cache.get(key)
                if result is not None:
                    return result
            except (RedisCircuitBreakerOpenError, RedisConnectionError) as e:
                logger.warning(f"Redis cache unavailable, falling back to memory cache: {str(e)}")
                self._redis_cache = None  # Temporarily disable Redis
            except Exception as e:
                logger.error(f"Error retrieving from Redis cache: {str(e)}")
        
        # Fall back to memory cache
        return await self._memory_cache.get(key)
        
    async def set(self, key: str, results: Dict[str, Any]) -> bool:
        """
        Store results in cache.
        
        Args:
            key: Cache key
            results: Results to cache
            
        Returns:
            True if stored successfully in any cache
        """
        # Ensure cache is initialized
        if not self._initialized:
            await self.initialize()
        
        success = False
        
        # Try to store in Redis if available
        if self._redis_cache is not None:
            try:
                redis_success = await self._redis_cache.set(key, results)
                success = redis_success
            except (RedisCircuitBreakerOpenError, RedisConnectionError) as e:
                logger.warning(f"Redis cache unavailable, falling back to memory cache: {str(e)}")
                self._redis_cache = None  # Temporarily disable Redis
            except Exception as e:
                logger.error(f"Error storing in Redis cache: {str(e)}")
        
        # Always store in memory cache as well (or as fallback)
        memory_success = await self._memory_cache.set(key, results)
        
        return success or memory_success
        
    async def generate_key(self, *args, **kwargs) -> str:
        """
        Generate a cache key from arguments.
        
        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Cache key string
        """
        # Use memory cache implementation for key generation
        return await self._memory_cache.generate_key(*args, **kwargs)


# Singleton cache instance - will be initialized during application startup
cache = HybridCache()


# Function to be called during application startup
async def initialize_cache() -> None:
    """Initialize the cache during application startup."""
    await cache.initialize()