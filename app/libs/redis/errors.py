"""
Redis-specific error classes.

This module defines exceptions specific to the Redis cache implementation.
"""


class RedisError(Exception):
    """Base class for Redis-related errors."""
    pass


class RedisConnectionError(RedisError):
    """Error connecting to Redis server."""
    pass


class RedisCircuitBreakerOpenError(RedisError):
    """Error indicating the circuit breaker is open."""
    pass


class RedisSerializationError(RedisError):
    """Error during serialization or deserialization of cache data."""
    pass


class RedisOperationError(RedisError):
    """Error during Redis operation."""
    pass