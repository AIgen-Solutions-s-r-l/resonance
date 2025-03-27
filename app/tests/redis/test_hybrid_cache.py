"""
Tests for the hybrid cache implementation.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.libs.job_matcher.cache import HybridCache, ResultsCache
from app.libs.redis.errors import (
    RedisConnectionError,
    RedisCircuitBreakerOpenError
)


@pytest.fixture
def mock_redis_cache():
    """Create a mock Redis cache."""
    redis_cache = AsyncMock()
    redis_cache.get.return_value = {"key": "redis_value"}
    redis_cache.set.return_value = True
    redis_cache.generate_key.return_value = "test_key_redis"
    return redis_cache


@pytest.fixture
def mock_memory_cache():
    """Create a mock memory cache."""
    memory_cache = AsyncMock(spec=ResultsCache)
    memory_cache.get.return_value = {"key": "memory_value"}
    memory_cache.set.return_value = True
    memory_cache.generate_key.return_value = "test_key_memory"
    return memory_cache


@pytest.fixture
def hybrid_cache(mock_redis_cache, mock_memory_cache):
    """Create a hybrid cache with mocked dependencies."""
    # Create the hybrid cache
    cache = HybridCache(ttl=300, max_size=1000)
    
    # Replace dependencies with mocks
    cache._redis_cache = mock_redis_cache
    cache._memory_cache = mock_memory_cache
    cache._initialized = True
    
    return cache


@pytest.mark.asyncio
@patch("app.libs.job_matcher.cache.init_redis_cache")
async def test_initialize(mock_initialize_cache):
    """Test the initialize method."""
    # Setup
    mock_redis_cache = AsyncMock()
    mock_initialize_cache.return_value = mock_redis_cache
    
    # Create cache without initialization
    cache = HybridCache()
    cache._initialized = False
    
    # Execute
    await cache.initialize()
    
    # Verify
    assert cache._initialized is True
    assert cache._redis_cache is not None
    mock_initialize_cache.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.libs.job_matcher.cache.init_redis_cache")
async def test_initialize_failure(mock_initialize_cache):
    """Test initialization failure."""
    # Setup
    mock_initialize_cache.return_value = None
    
    # Create cache without initialization
    cache = HybridCache()
    cache._initialized = False
    
    # Execute
    await cache.initialize()
    
    # Verify
    assert cache._initialized is True
    assert cache._redis_cache is None
    mock_initialize_cache.assert_awaited_once()

@pytest.mark.asyncio
@patch("app.libs.job_matcher.cache.init_redis_cache")
async def test_initialize_error(mock_initialize_cache):
    """Test initialization with error."""
    # Setup
    mock_initialize_cache.side_effect = Exception("Test error")
    
    # Create cache without initialization
    cache = HybridCache()
    cache._initialized = False
    
    # Execute
    await cache.initialize()
    
    # Verify
    assert cache._initialized is True
    assert cache._redis_cache is None
    mock_initialize_cache.assert_awaited_once()
    mock_initialize_cache.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_redis_cache_hit(hybrid_cache, mock_redis_cache):
    """Test get with Redis cache hit."""
    # Execute
    result = await hybrid_cache.get("test_key")
    
    # Verify
    assert result == {"key": "redis_value"}
    mock_redis_cache.get.assert_awaited_once_with("test_key")
    # Memory cache should not be called since Redis had a hit
    hybrid_cache._memory_cache.get.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_redis_cache_miss(hybrid_cache, mock_redis_cache):
    """Test get with Redis cache miss, memory cache hit."""
    # Setup
    mock_redis_cache.get.return_value = None
    
    # Execute
    result = await hybrid_cache.get("test_key")
    
    # Verify
    assert result == {"key": "memory_value"}
    mock_redis_cache.get.assert_awaited_once_with("test_key")
    # Memory cache should be called since Redis had a miss
    hybrid_cache._memory_cache.get.assert_awaited_once_with("test_key")


@pytest.mark.asyncio
async def test_get_redis_circuit_open(hybrid_cache, mock_redis_cache):
    """Test get with Redis circuit breaker open."""
    # Setup
    mock_redis_cache.get.side_effect = RedisCircuitBreakerOpenError("Circuit open")
    
    # Execute
    result = await hybrid_cache.get("test_key")
    
    # Verify
    assert result == {"key": "memory_value"}
    mock_redis_cache.get.assert_awaited_once_with("test_key")
    # Memory cache should be called due to circuit breaker
    hybrid_cache._memory_cache.get.assert_awaited_once_with("test_key")
    # Redis cache should be disabled
    assert hybrid_cache._redis_cache is None


@pytest.mark.asyncio
async def test_get_redis_connection_error(hybrid_cache, mock_redis_cache):
    """Test get with Redis connection error."""
    # Setup
    mock_redis_cache.get.side_effect = RedisConnectionError("Connection error")
    
    # Execute
    result = await hybrid_cache.get("test_key")
    
    # Verify
    assert result == {"key": "memory_value"}
    mock_redis_cache.get.assert_awaited_once_with("test_key")
    # Memory cache should be called due to connection error
    hybrid_cache._memory_cache.get.assert_awaited_once_with("test_key")
    # Redis cache should be disabled
    assert hybrid_cache._redis_cache is None


@pytest.mark.asyncio
async def test_get_redis_other_error(hybrid_cache, mock_redis_cache):
    """Test get with other Redis error."""
    # Setup
    mock_redis_cache.get.side_effect = Exception("Test error")
    
    # Execute
    result = await hybrid_cache.get("test_key")
    
    # Verify
    assert result == {"key": "memory_value"}
    mock_redis_cache.get.assert_awaited_once_with("test_key")
    # Memory cache should be called due to error
    hybrid_cache._memory_cache.get.assert_awaited_once_with("test_key")
    # Redis cache should not be disabled for other errors
    assert hybrid_cache._redis_cache is mock_redis_cache


@pytest.mark.asyncio
async def test_set_redis_available(hybrid_cache, mock_redis_cache):
    """Test set with Redis available."""
    # Execute
    result = await hybrid_cache.set("test_key", {"data": "test"})
    
    # Verify
    assert result is True
    mock_redis_cache.set.assert_awaited_once_with("test_key", {"data": "test"})
    # Memory cache should always be called
    hybrid_cache._memory_cache.set.assert_awaited_once_with("test_key", {"data": "test"})


@pytest.mark.asyncio
async def test_set_redis_circuit_open(hybrid_cache, mock_redis_cache):
    """Test set with Redis circuit breaker open."""
    # Setup
    mock_redis_cache.set.side_effect = RedisCircuitBreakerOpenError("Circuit open")
    
    # Execute
    result = await hybrid_cache.set("test_key", {"data": "test"})
    
    # Verify
    assert result is True  # Should still succeed due to memory cache
    mock_redis_cache.set.assert_awaited_once_with("test_key", {"data": "test"})
    # Memory cache should be called
    hybrid_cache._memory_cache.set.assert_awaited_once_with("test_key", {"data": "test"})
    # Redis cache should be disabled
    assert hybrid_cache._redis_cache is None


@pytest.mark.asyncio
async def test_set_redis_connection_error(hybrid_cache, mock_redis_cache):
    """Test set with Redis connection error."""
    # Setup
    mock_redis_cache.set.side_effect = RedisConnectionError("Connection error")
    
    # Execute
    result = await hybrid_cache.set("test_key", {"data": "test"})
    
    # Verify
    assert result is True  # Should still succeed due to memory cache
    mock_redis_cache.set.assert_awaited_once_with("test_key", {"data": "test"})
    # Memory cache should be called
    hybrid_cache._memory_cache.set.assert_awaited_once_with("test_key", {"data": "test"})
    # Redis cache should be disabled
    assert hybrid_cache._redis_cache is None


@pytest.mark.asyncio
async def test_set_redis_other_error(hybrid_cache, mock_redis_cache):
    """Test set with other Redis error."""
    # Setup
    mock_redis_cache.set.side_effect = Exception("Test error")
    
    # Execute
    result = await hybrid_cache.set("test_key", {"data": "test"})
    
    # Verify
    assert result is True  # Should still succeed due to memory cache
    mock_redis_cache.set.assert_awaited_once_with("test_key", {"data": "test"})
    # Memory cache should be called
    hybrid_cache._memory_cache.set.assert_awaited_once_with("test_key", {"data": "test"})
    # Redis cache should not be disabled for other errors
    assert hybrid_cache._redis_cache is mock_redis_cache


@pytest.mark.asyncio
async def test_set_all_caches_fail(hybrid_cache, mock_redis_cache):
    """Test set with all caches failing."""
    # Setup
    mock_redis_cache.set.side_effect = Exception("Redis error")
    hybrid_cache._memory_cache.set.return_value = False
    
    # Execute
    result = await hybrid_cache.set("test_key", {"data": "test"})
    
    # Verify
    assert result is False
    mock_redis_cache.set.assert_awaited_once_with("test_key", {"data": "test"})
    hybrid_cache._memory_cache.set.assert_awaited_once_with("test_key", {"data": "test"})


@pytest.mark.asyncio
async def test_generate_key(hybrid_cache):
    """Test generate_key method."""
    # Execute
    result = await hybrid_cache.generate_key("test", param="value")
    
    # Verify
    assert result == "test_key_memory"
    hybrid_cache._memory_cache.generate_key.assert_awaited_once_with("test", param="value")