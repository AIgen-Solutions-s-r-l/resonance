"""
Tests for the Redis cache implementation.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch, call

from app.libs.redis.cache import RedisCache
from app.libs.redis.errors import (
    RedisConnectionError, 
    RedisCircuitBreakerOpenError,
    RedisSerializationError
)


@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client."""
    redis_mock = AsyncMock()
    redis_mock.get.return_value = '{"key": "value"}'
    redis_mock.setex.return_value = True
    redis_mock.delete.return_value = 1
    redis_mock.scan.return_value = (0, ["test:key1", "test:key2"])
    return redis_mock


@pytest.fixture
def mock_connection_manager(mock_redis_client):
    """Create a mock connection manager."""
    manager = AsyncMock()
    manager.get_redis.return_value = mock_redis_client
    return manager


@pytest.fixture
def redis_cache(mock_connection_manager):
    """Create a Redis cache instance with mocked dependencies."""
    return RedisCache(
        connection_manager=mock_connection_manager,
        ttl=300,
        max_retries=2,
        initial_backoff_ms=10,
        max_backoff_ms=100,
        namespace="test"
    )


@pytest.mark.asyncio
async def test_get_success(redis_cache, mock_connection_manager, mock_redis_client):
    """Test successful cache get operation."""
    # Setup
    mock_redis_client.get.return_value = '{"data": "test_value"}'
    
    # Execute
    result = await redis_cache.get("test_key")
    
    # Verify
    assert result == {"data": "test_value"}
    mock_connection_manager.get_redis.assert_awaited_once()
    mock_redis_client.get.assert_awaited_once_with("test:test_key")


@pytest.mark.asyncio
async def test_get_miss(redis_cache, mock_redis_client):
    """Test cache miss."""
    # Setup
    mock_redis_client.get.return_value = None
    
    # Execute
    result = await redis_cache.get("test_key")
    
    # Verify
    assert result is None
    mock_redis_client.get.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_deserialization_error(redis_cache, mock_redis_client):
    """Test handling of deserialization error during get."""
    # Setup - invalid JSON
    mock_redis_client.get.return_value = '{invalid:json}'
    
    # Execute
    result = await redis_cache.get("test_key")
    
    # Verify
    assert result is None
    mock_redis_client.delete.assert_awaited_once()  # Should delete corrupted data


@pytest.mark.asyncio
@patch("asyncio.sleep")
async def test_get_with_retry(mock_sleep, redis_cache, mock_connection_manager, mock_redis_client):
    """Test retry mechanism for get operation."""
    # Setup - first call fails, second succeeds
    mock_redis_client.get.side_effect = [
        RedisConnectionError("Connection error"),
        '{"data": "retry_success"}'
    ]
    
    # Execute
    result = await redis_cache.get("test_key")
    
    # Verify
    assert result == {"data": "retry_success"}
    assert mock_redis_client.get.await_count == 2
    mock_sleep.assert_awaited_once()  # Should have slept once for retry


@pytest.mark.asyncio
@patch("asyncio.sleep")
async def test_get_max_retries_exceeded(mock_sleep, redis_cache, mock_redis_client):
    """Test behavior when max retries are exceeded for get operation."""
    # Setup - all calls fail
    mock_redis_client.get.side_effect = RedisConnectionError("Connection error")
    
    # Execute
    result = await redis_cache.get("test_key")
    
    # Verify
    assert result is None
    assert mock_redis_client.get.await_count == 3  # Initial + 2 retries
    assert mock_sleep.await_count == 2  # Should have slept twice for retries


@pytest.mark.asyncio
async def test_get_circuit_breaker_open(redis_cache, mock_connection_manager):
    """Test get operation when circuit breaker is open."""
    # Setup
    mock_connection_manager.get_redis.side_effect = RedisCircuitBreakerOpenError("Circuit open")
    
    # Execute
    result = await redis_cache.get("test_key")
    
    # Verify
    assert result is None
    mock_connection_manager.get_redis.assert_awaited_once()


@pytest.mark.asyncio
async def test_set_success(redis_cache, mock_connection_manager, mock_redis_client):
    """Test successful cache set operation."""
    # Execute
    result = await redis_cache.set("test_key", {"data": "test_value"})
    
    # Verify
    assert result is True
    mock_connection_manager.get_redis.assert_awaited_once()
    mock_redis_client.setex.assert_awaited_once()
    # Verify the key has namespace prefix
    args = mock_redis_client.setex.await_args.args
    assert args[0] == "test:test_key"
    assert args[1] == 300  # TTL


@pytest.mark.asyncio
@patch("app.libs.redis.serialization.RedisSerializer.serialize")
async def test_set_serialization_error(mock_serialize, redis_cache):
    """Test handling of serialization error during set."""
    # Setup
    mock_serialize.side_effect = RedisSerializationError("Cannot serialize")
    
    # Execute
    result = await redis_cache.set("test_key", {"data": "test_value"})
    
    # Verify
    assert result is False


@pytest.mark.asyncio
@patch("asyncio.sleep")
async def test_set_with_retry(mock_sleep, redis_cache, mock_connection_manager, mock_redis_client):
    """Test retry mechanism for set operation."""
    # Setup - first call fails, second succeeds
    mock_redis_client.setex.side_effect = [
        RedisConnectionError("Connection error"),
        True
    ]
    
    # Execute
    result = await redis_cache.set("test_key", {"data": "test_value"})
    
    # Verify
    assert result is True
    assert mock_redis_client.setex.await_count == 2
    mock_sleep.assert_awaited_once()  # Should have slept once for retry


@pytest.mark.asyncio
@patch("asyncio.sleep")
async def test_set_max_retries_exceeded(mock_sleep, redis_cache, mock_redis_client):
    """Test behavior when max retries are exceeded for set operation."""
    # Setup - all calls fail
    mock_redis_client.setex.side_effect = RedisConnectionError("Connection error")
    
    # Execute
    result = await redis_cache.set("test_key", {"data": "test_value"})
    
    # Verify
    assert result is False
    assert mock_redis_client.setex.await_count == 3  # Initial + 2 retries
    assert mock_sleep.await_count == 2  # Should have slept twice for retries


@pytest.mark.asyncio
async def test_set_circuit_breaker_open(redis_cache, mock_connection_manager):
    """Test set operation when circuit breaker is open."""
    # Setup
    mock_connection_manager.get_redis.side_effect = RedisCircuitBreakerOpenError("Circuit open")
    
    # Execute
    result = await redis_cache.set("test_key", {"data": "test_value"})
    
    # Verify
    assert result is False
    mock_connection_manager.get_redis.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_success(redis_cache, mock_connection_manager, mock_redis_client):
    """Test successful cache delete operation."""
    # Execute
    result = await redis_cache.delete("test_key")
    
    # Verify
    assert result is True
    mock_connection_manager.get_redis.assert_awaited_once()
    mock_redis_client.delete.assert_awaited_once_with("test:test_key")


@pytest.mark.asyncio
async def test_delete_with_error(redis_cache, mock_redis_client):
    """Test delete operation with Redis error."""
    # Setup
    mock_redis_client.delete.side_effect = RedisConnectionError("Connection error")
    
    # Execute
    result = await redis_cache.delete("test_key")
    
    # Verify
    assert result is False
    mock_redis_client.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_circuit_breaker_open(redis_cache, mock_connection_manager):
    """Test delete operation when circuit breaker is open."""
    # Setup
    mock_connection_manager.get_redis.side_effect = RedisCircuitBreakerOpenError("Circuit open")
    
    # Execute
    result = await redis_cache.delete("test_key")
    
    # Verify
    assert result is False
    mock_connection_manager.get_redis.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_key(redis_cache):
    """Test key generation."""
    # Test with various inputs
    key1 = await redis_cache.generate_key("user", 123, location="New York")
    key2 = await redis_cache.generate_key("user", 123, location="Boston")
    key3 = await redis_cache.generate_key("product", 456)
    
    # Verify keys are different
    assert key1 != key2
    assert key1 != key3
    assert key2 != key3
    
    # Verify key format
    assert "user" in key1
    assert "123" in key1
    assert "location_New York" in key1


@pytest.mark.asyncio
async def test_clear_namespace(redis_cache, mock_connection_manager, mock_redis_client):
    """Test clearing all keys in a namespace."""
    # Execute
    result = await redis_cache.clear_namespace()
    
    # Verify
    assert result is True
    mock_connection_manager.get_redis.assert_awaited_once()
    mock_redis_client.scan.assert_awaited_once()
    mock_redis_client.delete.assert_awaited_once_with("test:key1", "test:key2")


@pytest.mark.asyncio
async def test_clear_namespace_with_error(redis_cache, mock_redis_client):
    """Test namespace clearing with Redis error."""
    # Setup
    mock_redis_client.scan.side_effect = RedisConnectionError("Connection error")
    
    # Execute
    result = await redis_cache.clear_namespace()
    
    # Verify
    assert result is False
    mock_redis_client.scan.assert_awaited_once()


@pytest.mark.asyncio
async def test_clear_namespace_no_namespace_set():
    """Test behavior when trying to clear namespace but none is set."""
    # Create cache without namespace
    cache = RedisCache(
        connection_manager=AsyncMock(),
        namespace=None
    )
    
    # Execute
    result = await cache.clear_namespace()
    
    # Verify
    assert result is False  # Should fail since no namespace is set