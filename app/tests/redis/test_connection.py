"""
Tests for the Redis connection manager.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from redis.asyncio.client import Redis
from redis.exceptions import ConnectionError as RedisConnectionError, RedisError

from app.libs.redis.connection import RedisConnectionManager
from app.libs.redis.circuit_breaker import CircuitBreaker, CircuitState
from app.libs.redis.errors import RedisCircuitBreakerOpenError


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    # Create a proper AsyncMock with all needed methods
    redis_mock = AsyncMock(spec=Redis)
    
    # Fix ping to be properly awaitable and return True
    async def mock_ping():
        return True
    redis_mock.ping = AsyncMock(side_effect=mock_ping)
    
    # Make close properly awaitable
    async def mock_close():
        return True
    redis_mock.close = AsyncMock(side_effect=mock_close)
    
    return redis_mock


@pytest.fixture
def mock_circuit_breaker():
    """Create a mock circuit breaker."""
    circuit_breaker = AsyncMock(spec=CircuitBreaker)
    
    # Make is_allowed properly awaitable
    async def mock_is_allowed():
        return True
    circuit_breaker.is_allowed = AsyncMock(side_effect=mock_is_allowed)
    
    # Make record_success properly awaitable
    async def mock_record_success():
        return None
    circuit_breaker.record_success = AsyncMock(side_effect=mock_record_success)
    
    # Make record_failure properly awaitable
    async def mock_record_failure():
        return None
    circuit_breaker.record_failure = AsyncMock(side_effect=mock_record_failure)
    
    return circuit_breaker


@pytest.fixture
def connection_manager(mock_circuit_breaker):
    """Create a connection manager with a mock circuit breaker."""
    return RedisConnectionManager(
        host="localhost",
        port=6379,
        circuit_breaker=mock_circuit_breaker
    )


@pytest.mark.asyncio
async def test_initialize_success(connection_manager, mock_redis):
    """Test successful initialization of Redis connection."""
    # Replace _create_redis_client with our own implementation to bypass from_url
    async def mock_create_client():
        return mock_redis
    
    # Patch the method directly on the instance
    connection_manager._create_redis_client = mock_create_client
    
    # Call initialize
    result = await connection_manager.initialize()
    
    # Verify
    assert result is True
    assert connection_manager._client is mock_redis
    assert mock_redis.ping.call_count == 1


@pytest.mark.asyncio
@patch("redis.asyncio.from_url")
async def test_initialize_failure(mock_from_url, connection_manager):
    """Test initialization failure with Redis error."""
    # Setup mock to raise error
    mock_from_url.side_effect = RedisConnectionError("Failed to connect")
    
    # Call initialize
    result = await connection_manager.initialize()
    
    # Verify
    assert result is False
    assert connection_manager._client is None


@pytest.mark.asyncio
async def test_get_redis_not_initialized(connection_manager):
    """Test getting Redis client when not initialized."""
    connection_manager._client = None
    
    # Should raise exception
    with pytest.raises(Exception):
        await connection_manager.get_redis()

@pytest.mark.asyncio
async def test_get_redis_circuit_open(connection_manager, mock_circuit_breaker):
    """Test getting Redis client when circuit breaker is open."""
    # Setup client but circuit breaker is open
    connection_manager._client = AsyncMock()
    
    # Override the is_allowed method to return False
    async def mock_is_allowed_false():
        return False
    mock_circuit_breaker.is_allowed = AsyncMock(side_effect=mock_is_allowed_false)
    
    # Should raise circuit breaker error
    with pytest.raises(RedisCircuitBreakerOpenError):
        await connection_manager.get_redis()


@pytest.mark.asyncio
async def test_get_redis_success(connection_manager, mock_redis):
    """Test successfully getting Redis client."""
    # Setup
    connection_manager._client = mock_redis
    
    # Get Redis client
    client = await connection_manager.get_redis()
    
    # Verify
    assert client is mock_redis

@pytest.mark.asyncio
async def test_health_check_success(connection_manager, mock_redis):
    """Test successful health check."""
    # Setup a mock for asyncio.sleep that executes the health check immediately
    original_sleep = asyncio.sleep
    
    # Create a counter to track sleep calls
    sleep_counter = 0
    
    async def mock_sleep(seconds):
        nonlocal sleep_counter
        sleep_counter += 1
        if sleep_counter > 1:  # Allow one iteration then stop
            raise asyncio.CancelledError()
        return None
        
    # Patch asyncio.sleep
    asyncio.sleep = mock_sleep
    
    try:
        # Setup Redis client
        connection_manager._client = mock_redis
        connection_manager._health_check_interval = 0.1
        
        try:
            # Run health check directly (without task)
            await connection_manager._health_check_loop()
        except asyncio.CancelledError:
            # Expected after one iteration
            pass
        
        # Verify health check was performed
        assert mock_redis.ping.call_count > 0
    finally:
        # Restore original sleep
        asyncio.sleep = original_sleep

@pytest.mark.asyncio
async def test_health_check_failure(connection_manager, mock_redis, mock_circuit_breaker):
    """Test health check with Redis failure."""
    # Setup a mock for asyncio.sleep that executes the health check immediately
    original_sleep = asyncio.sleep
    
    # Create a counter to track sleep calls
    sleep_counter = 0
    
    async def mock_sleep(seconds):
        nonlocal sleep_counter
        sleep_counter += 1
        if sleep_counter > 1:  # Allow one iteration then stop
            raise asyncio.CancelledError()
        return None
    
    # Patch asyncio.sleep
    asyncio.sleep = mock_sleep
    
    try:
        # Setup Redis client with error
        connection_manager._client = mock_redis
        connection_manager._health_check_interval = 0.1
        
        # Make ping raise an error
        async def mock_ping_error():
            raise RedisError("Health check failed")
        mock_redis.ping = AsyncMock(side_effect=mock_ping_error)
        
        try:
            # Run health check directly (without task)
            await connection_manager._health_check_loop()
        except asyncio.CancelledError:
            # Expected after one iteration
            pass
        
        # Verify failure was recorded
        assert mock_circuit_breaker.record_failure.call_count > 0
    finally:
        # Restore original sleep
        asyncio.sleep = original_sleep


@pytest.mark.asyncio
async def test_close(connection_manager, mock_redis):
    """Test closing Redis connection."""
    # Setup
    connection_manager._client = mock_redis
    connection_manager._health_check_task = asyncio.create_task(asyncio.sleep(1))
    
    # Close connection
    await connection_manager.close()
    
    # Verify
    assert mock_redis.close.call_count == 1
    assert connection_manager._client is None
    assert connection_manager._health_check_task is None
@pytest.mark.asyncio
async def test_reconnect_success(connection_manager, mock_redis):
    """Test successful reconnection to Redis."""
    # Setup - use a proper AsyncMock for _create_redis_client
    async def mock_create_client():
        return mock_redis
    
    # Patch the method directly on the instance
    connection_manager._create_redis_client = mock_create_client
    connection_manager._client = None
    
    # Try to reconnect
    result = await connection_manager._try_reconnect()
    
    # Verify
    assert result is True
    assert connection_manager._client is mock_redis
    # We can't use assert_awaited_once() directly on a function


@pytest.mark.asyncio
async def test_reconnect_failure(connection_manager, mock_circuit_breaker):
    """Test reconnection failure."""
    # Setup - use a proper implementation that raises an exception
    async def mock_create_client_error():
        raise RedisConnectionError("Failed to reconnect")
    
    # Patch the method directly on the instance
    connection_manager._create_redis_client = mock_create_client_error
    connection_manager._client = None
    
    # Try to reconnect
    result = await connection_manager._try_reconnect()
    
    # Verify
    assert result is False
    assert connection_manager._client is None
    assert mock_circuit_breaker.record_failure.call_count > 0