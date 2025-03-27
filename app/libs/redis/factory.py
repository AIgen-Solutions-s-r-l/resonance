"""
Redis cache factory for creating and managing cache instances.

This module provides a factory for creating Redis cache instances with
proper configuration from application settings. It also maintains singleton
instances for reuse.
"""

from typing import Dict, Optional

from loguru import logger

from app.core.config import settings
from app.libs.redis.cache import RedisCache
from app.libs.redis.connection import RedisConnectionManager
from app.libs.redis.circuit_breaker import CircuitBreaker


class RedisCacheFactory:
    """
    Factory for creating and managing Redis cache instances.
    
    This class provides methods for creating properly configured Redis cache
    instances based on application settings. It also maintains a connection
    manager singleton for reuse.
    """
    
    # Singleton connection manager
    _connection_manager: Optional[RedisConnectionManager] = None
    
    # Cache of created caches by namespace
    _caches: Dict[str, RedisCache] = {}
    
    # Flag to track initialization
    _initialized = False
    
    @classmethod
    async def initialize(cls) -> bool:
        """
        Initialize the Redis connection manager.
        
        Returns:
            True if initialization successful, False otherwise
        """
        if cls._initialized:
            return True
            
        # Create connection manager if needed
        if cls._connection_manager is None:
            # Create circuit breaker
            circuit_breaker = CircuitBreaker(
                failure_threshold=5,
                reset_timeout=30
            )
            
            # Create connection manager
            cls._connection_manager = RedisConnectionManager(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password,
                max_connections=10,
                connection_timeout=2.0,
                health_check_interval=30,
                circuit_breaker=circuit_breaker
            )
        
        # Initialize connection
        success = await cls._connection_manager.initialize()
        
        if success:
            cls._initialized = True
            logger.info("Redis cache factory initialized successfully")
        else:
            logger.error("Failed to initialize Redis cache factory")
            
        return success
    
    @classmethod
    async def create_cache(
        cls,
        ttl: int = 300,
        namespace: Optional[str] = None,
        max_retries: int = 3
    ) -> RedisCache:
        """
        Create a new Redis cache instance.
        
        Args:
            ttl: Cache TTL in seconds
            namespace: Optional namespace prefix for cache keys
            max_retries: Maximum number of retry attempts
            
        Returns:
            Configured Redis cache instance
        """
        # Use existing cache instance if available for this namespace
        cache_key = f"{namespace or 'default'}:{ttl}:{max_retries}"
        if cache_key in cls._caches:
            return cls._caches[cache_key]
        
        # Initialize if needed
        if not cls._initialized:
            await cls.initialize()
        
        # Create new cache instance
        cache = RedisCache(
            connection_manager=cls._connection_manager,
            ttl=ttl,
            max_retries=max_retries,
            initial_backoff_ms=100,
            max_backoff_ms=30000,
            namespace=namespace
        )
        
        # Store in cache
        cls._caches[cache_key] = cache
        
        logger.info(
            f"Created Redis cache instance with namespace={namespace or 'default'}, "
            f"ttl={ttl}s, max_retries={max_retries}"
        )
        
        return cache
    
    @classmethod
    async def close(cls) -> None:
        """Close all Redis connections."""
        if cls._connection_manager is not None:
            await cls._connection_manager.close()
            cls._connection_manager = None
            cls._caches = {}
            cls._initialized = False
            logger.info("Closed all Redis connections")


# Default singleton cache instance
cache: Optional[RedisCache] = None


async def initialize_cache() -> Optional[RedisCache]:
    """
    Initialize the default Redis cache instance.
    
    Returns:
        Initialized Redis cache instance or None if initialization fails
    """
    global cache
    
    try:
        if not await RedisCacheFactory.initialize():
            logger.error("Failed to initialize Redis, cache will not be available")
            return None
            
        cache = await RedisCacheFactory.create_cache(
            ttl=300,
            namespace="matching",
            max_retries=3
        )
        
        logger.info("Default Redis cache initialized")
        return cache
        
    except Exception as e:
        logger.exception(f"Error initializing Redis cache: {str(e)}")
        return None