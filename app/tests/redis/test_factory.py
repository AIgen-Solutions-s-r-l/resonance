"""
Tests for the Redis cache factory.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.libs.redis.factory import RedisCacheFactory
from app.libs.redis.cache import RedisCache
from app.libs.redis.errors import RedisConnectionError


@pytest.fixture
async def mock_connection_manager():
    """Create a mock connection manager."""
    manager = AsyncMock()
    manager.initialize.return_value = True
    return manager


@pytest.mark.asyncio
@patch("app.libs.redis.factory.RedisConnectionManager")
async def test_initialize_success(mock_manager_class):
    """Test successful initialization of factory."""
    # Setup
    manager_instance = AsyncMock()
    manager_instance.initialize.return_value = True
    mock_manager_class.return_value = manager_instance
    
    # Reset singleton state
    RedisCacheFactory._connection_manager = None
    RedisCacheFactory._initialized = False
    
    # Execute
    result = await RedisCacheFactory.initialize()
    
    # Verify
    assert result is True
    assert RedisCacheFactory._initialized is True
    assert RedisCacheFactory._connection_manager is manager_instance
    manager_instance.initialize.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.libs.redis.factory.RedisConnectionManager")
async def test_initialize_failure(mock_manager_class):
    """Test factory initialization failure."""
    # Setup
    manager_instance = AsyncMock()
    manager_instance.initialize.return_value = False
    mock_manager_class.return_value = manager_instance
    
    # Reset singleton state
    RedisCacheFactory._connection_manager = None
    RedisCacheFactory._initialized = False
    
    # Execute
    result = await RedisCacheFactory.initialize()
    
    # Verify
    assert result is False
    assert RedisCacheFactory._initialized is False
    manager_instance.initialize.assert_awaited_once()


@pytest.mark.asyncio
async def test_initialize_already_initialized():
    """Test initialize when already initialized."""
    # Setup - manually set initialized state
    RedisCacheFactory._initialized = True
    RedisCacheFactory._connection_manager = AsyncMock()
    
    # Execute
    result = await RedisCacheFactory.initialize()
    
    # Verify
    assert result is True
    # Connection manager shouldn't be recreated
    assert RedisCacheFactory._connection_manager is not None


@pytest.mark.asyncio
@patch("app.libs.redis.factory.RedisConnectionManager")
async def test_create_cache_with_initialization(mock_manager_class):
    """Test create_cache with automatic initialization."""
    # Setup
    manager_instance = AsyncMock()
    manager_instance.initialize.return_value = True
    mock_manager_class.return_value = manager_instance
    
    # Reset singleton state
    RedisCacheFactory._connection_manager = None
    RedisCacheFactory._initialized = False
    RedisCacheFactory._caches = {}
    
    # Execute
    cache = await RedisCacheFactory.create_cache(ttl=600, namespace="test")
    
    # Verify
    assert isinstance(cache, RedisCache)
    assert RedisCacheFactory._initialized is True
    # Cache should be stored in the cache dictionary
    assert len(RedisCacheFactory._caches) == 1
    assert "test:600:3" in RedisCacheFactory._caches


@pytest.mark.asyncio
async def test_create_cache_reuse_existing():
    """Test that create_cache reuses existing cache instances."""
    # Setup - manually set initialized state and create a mock cache
    RedisCacheFactory._initialized = True
    RedisCacheFactory._connection_manager = AsyncMock()
    mock_cache = MagicMock()
    RedisCacheFactory._caches = {"test:300:3": mock_cache}
    
    # Execute
    cache1 = await RedisCacheFactory.create_cache(namespace="test")
    cache2 = await RedisCacheFactory.create_cache(namespace="test")
    
    # Verify
    assert cache1 is mock_cache
    assert cache2 is mock_cache
    assert cache1 is cache2  # Same instance returned


@pytest.mark.asyncio
async def test_create_cache_different_settings():
    """Test that create_cache creates new instances for different settings."""
    # Setup - manually set initialized state
    RedisCacheFactory._initialized = True
    RedisCacheFactory._connection_manager = AsyncMock()
    RedisCacheFactory._caches = {}
    
    # Execute
    cache1 = await RedisCacheFactory.create_cache(namespace="test1")
    cache2 = await RedisCacheFactory.create_cache(namespace="test2")
    cache3 = await RedisCacheFactory.create_cache(namespace="test1", ttl=600)
    
    # Verify
    assert cache1 is not cache2  # Different namespaces
    assert cache1 is not cache3  # Different TTLs
    assert len(RedisCacheFactory._caches) == 3


@pytest.mark.asyncio
async def test_close():
    """Test closing all Redis connections."""
    # Setup
    mock_connection_manager = AsyncMock()
    RedisCacheFactory._connection_manager = mock_connection_manager
    RedisCacheFactory._initialized = True
    RedisCacheFactory._caches = {"test": MagicMock()}
    
    # Execute
    await RedisCacheFactory.close()
    
    # Verify
    mock_connection_manager.close.assert_awaited_once()
    assert RedisCacheFactory._connection_manager is None
    assert RedisCacheFactory._initialized is False
    assert RedisCacheFactory._caches == {}


@pytest.mark.asyncio
@patch("app.libs.redis.factory.RedisCacheFactory.initialize")
async def test_initialize_cache_success(mock_initialize):
    """Test initialize_cache global function success."""
    # Setup
    from app.libs.redis.factory import initialize_cache
    mock_initialize.return_value = True
    
    # Replace the create_cache method
    original_create_cache = RedisCacheFactory.create_cache
    mock_cache = MagicMock()
    
    async def mock_create_cache(*args, **kwargs):
        return mock_cache
        
    RedisCacheFactory.create_cache = mock_create_cache
    
    try:
        # Execute
        result = await initialize_cache()
        
        # Verify
        assert result is mock_cache
        mock_initialize.assert_awaited_once()
    finally:
        # Restore original method
        RedisCacheFactory.create_cache = original_create_cache


@pytest.mark.asyncio
@patch("app.libs.redis.factory.RedisCacheFactory.initialize")
async def test_initialize_cache_failure(mock_initialize):
    """Test initialize_cache global function failure."""
    # Setup
    from app.libs.redis.factory import initialize_cache
    mock_initialize.return_value = False
    
    # Execute
    result = await initialize_cache()
    
    # Verify
    assert result is None
    mock_initialize.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.libs.redis.factory.RedisCacheFactory.initialize")
async def test_initialize_cache_exception(mock_initialize):
    """Test initialize_cache global function with exception."""
    # Setup
    from app.libs.redis.factory import initialize_cache
    mock_initialize.side_effect = Exception("Test error")
    
    # Execute
    result = await initialize_cache()
    
    # Verify
    assert result is None
    mock_initialize.assert_awaited_once()