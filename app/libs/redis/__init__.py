"""
Redis caching package.

This package provides Redis-based caching functionality with automatic 
serialization, TTL management, and error handling.
"""

from app.libs.redis.cache import RedisCache
from app.libs.redis.factory import RedisCacheFactory, initialize_cache
from app.libs.redis.errors import (
    RedisError, 
    RedisConnectionError,
    RedisCircuitBreakerOpenError,
    RedisSerializationError,
    RedisOperationError
)
from app.libs.redis.circuit_breaker import CircuitBreaker, CircuitState
from app.libs.redis.monitoring import (
    RedisMetrics,
    RedisCacheMetricsMiddleware,
    create_metrics_wrapped_cache
)

__all__ = [
    'RedisCache',
    'RedisCacheFactory',
    'initialize_cache',
    'RedisError',
    'RedisConnectionError', 
    'RedisCircuitBreakerOpenError',
    'RedisSerializationError',
    'RedisOperationError',
    'CircuitBreaker',
    'CircuitState',
    'RedisMetrics',
    'RedisCacheMetricsMiddleware',
    'create_metrics_wrapped_cache'
]