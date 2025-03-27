"""
Tests for the Redis monitoring module.
"""

import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

from app.libs.redis.monitoring import (
    RedisMetrics,
    timed_cache_operation,
    RedisCacheMetricsMiddleware,
    create_metrics_wrapped_cache
)


@pytest.fixture
def mock_metrics():
    """Create a mock for the metrics system."""
    with patch("app.libs.redis.monitoring.metrics") as mock_metrics:
        # Ensure HAS_METRICS is True during tests
        with patch("app.libs.redis.monitoring.HAS_METRICS", True):
            yield mock_metrics


@pytest.fixture
def mock_cache():
    """Create a mock cache instance."""
    cache = AsyncMock()
    cache.get.return_value = {"key": "value"}
    cache.set.return_value = True
    cache.generate_key.return_value = "test_key"
    return cache


class TestRedisMetrics:
    """Test suite for the RedisMetrics class."""

    def test_increment_with_metrics(self, mock_metrics):
        """Test increment method when metrics system is available."""
        # Setup
        RedisMetrics.increment("redis.cache.hit", 1, namespace="test")
        
        # Verify
        mock_metrics.increment.assert_called_once_with(
            "redis.cache.hit", 1, namespace="test"
        )

    @patch("app.libs.redis.monitoring.HAS_METRICS", False)
    @patch("app.libs.redis.monitoring.logger")
    def test_increment_without_metrics(self, mock_logger):
        """Test increment method when metrics system is not available."""
        # Setup - patch HAS_METRICS to False
        RedisMetrics.increment("redis.cache.hit", 1, namespace="test")
        
        # Verify
        mock_logger.debug.assert_called_once()

    def test_timing_with_metrics(self, mock_metrics):
        """Test timing method when metrics system is available."""
        # Setup
        RedisMetrics.timing("redis.cache.get_latency", 10.5, namespace="test")
        
        # Verify
        mock_metrics.timing.assert_called_once_with(
            "redis.cache.get_latency", 10.5, namespace="test"
        )

    @patch("app.libs.redis.monitoring.HAS_METRICS", False)
    @patch("app.libs.redis.monitoring.logger")
    def test_timing_without_metrics(self, mock_logger):
        """Test timing method when metrics system is not available."""
        # Setup - patch HAS_METRICS to False
        RedisMetrics.timing("redis.cache.get_latency", 10.5, namespace="test")
        
        # Verify
        mock_logger.debug.assert_called_once()

    def test_gauge_with_metrics(self, mock_metrics):
        """Test gauge method when metrics system is available."""
        # Setup
        RedisMetrics.gauge("redis.cache.size", 100, namespace="test")
        
        # Verify
        mock_metrics.gauge.assert_called_once_with(
            "redis.cache.size", 100, namespace="test"
        )

    @patch("app.libs.redis.monitoring.HAS_METRICS", False)
    @patch("app.libs.redis.monitoring.logger")
    def test_gauge_without_metrics(self, mock_logger):
        """Test gauge method when metrics system is not available."""
        # Setup - patch HAS_METRICS to False
        RedisMetrics.gauge("redis.cache.size", 100, namespace="test")
        
        # Verify
        mock_logger.debug.assert_called_once()


@pytest.mark.asyncio
@patch("app.libs.redis.monitoring.RedisMetrics")
async def test_timed_cache_operation_success(mock_redis_metrics):
    """Test timed_cache_operation decorator with successful operation."""
    # Create a decorated function
    @timed_cache_operation("test_metric")
    async def test_func():
        return "success"
    
    # Execute
    result = await test_func()
    
    # Verify
    assert result == "success"
    # Should have timed the operation
    mock_redis_metrics.timing.assert_called_once()
    assert mock_redis_metrics.timing.call_args[0][0] == "test_metric"


@pytest.mark.asyncio
@patch("app.libs.redis.monitoring.RedisMetrics")
async def test_timed_cache_operation_error(mock_redis_metrics):
    """Test timed_cache_operation decorator with operation error."""
    # Create a decorated function that raises an error
    @timed_cache_operation("test_metric")
    async def test_func():
        raise ValueError("Test error")
    
    # Execute
    with pytest.raises(ValueError):
        await test_func()
    
    # Verify
    # Should have timed the operation
    mock_redis_metrics.timing.assert_called_once()
    # Should have recorded an error
    mock_redis_metrics.increment.assert_called_once_with(
        "redis.cache.error", 1, operation="test_metric", error="ValueError"
    )


class TestRedisCacheMetricsMiddleware:
    """Test suite for the RedisCacheMetricsMiddleware class."""

    @pytest.mark.asyncio
    @patch("app.libs.redis.monitoring.RedisMetrics")
    async def test_get_success(self, mock_redis_metrics, mock_cache):
        """Test get method with successful cache hit."""
        # Setup
        middleware = RedisCacheMetricsMiddleware(mock_cache)
        mock_cache.get.return_value = {"key": "value"}
        
        # Execute
        result = await middleware.get("test_key")
        
        # Verify
        assert result == {"key": "value"}
        mock_cache.get.assert_awaited_once_with("test_key")
        # Should have incremented the hit counter
        mock_redis_metrics.increment.assert_called_once_with("redis.cache.hit", 1)

    @pytest.mark.asyncio
    @patch("app.libs.redis.monitoring.RedisMetrics")
    async def test_get_miss(self, mock_redis_metrics, mock_cache):
        """Test get method with cache miss."""
        # Setup
        middleware = RedisCacheMetricsMiddleware(mock_cache)
        mock_cache.get.return_value = None
        
        # Execute
        result = await middleware.get("test_key")
        
        # Verify
        assert result is None
        mock_cache.get.assert_awaited_once_with("test_key")
        # Should have incremented the miss counter
        mock_redis_metrics.increment.assert_called_once_with("redis.cache.miss", 1)

    @pytest.mark.asyncio
    @patch("app.libs.redis.monitoring.RedisMetrics")
    async def test_get_error(self, mock_redis_metrics, mock_cache):
        """Test get method with error."""
        # Setup
        middleware = RedisCacheMetricsMiddleware(mock_cache)
        mock_cache.get.side_effect = Exception("Test error")
        
        # Execute
        with pytest.raises(Exception):
            await middleware.get("test_key")
        
        # Verify
        mock_cache.get.assert_awaited_once_with("test_key")
        # Should have incremented the error counter
        mock_redis_metrics.increment.assert_called_once_with(
            "redis.cache.error", 1, operation="get", error="Exception"
        )

    @pytest.mark.asyncio
    @patch("app.libs.redis.monitoring.RedisMetrics")
    async def test_set(self, mock_redis_metrics, mock_cache):
        """Test set method."""
        # Setup
        middleware = RedisCacheMetricsMiddleware(mock_cache)
        
        # Execute
        result = await middleware.set("test_key", {"key": "value"})
        
        # Verify
        assert result is True
        mock_cache.set.assert_awaited_once_with("test_key", {"key": "value"})

    @pytest.mark.asyncio
    @patch("app.libs.redis.monitoring.RedisMetrics")
    async def test_set_error(self, mock_redis_metrics, mock_cache):
        """Test set method with error."""
        # Setup
        middleware = RedisCacheMetricsMiddleware(mock_cache)
        mock_cache.set.side_effect = Exception("Test error")
        
        # Execute
        with pytest.raises(Exception):
            await middleware.set("test_key", {"key": "value"})
        
        # Verify
        mock_cache.set.assert_awaited_once_with("test_key", {"key": "value"})
        # Should have incremented the error counter
        mock_redis_metrics.increment.assert_called_once_with(
            "redis.cache.error", 1, operation="set", error="Exception"
        )

    @pytest.mark.asyncio
    async def test_generate_key(self, mock_cache):
        """Test generate_key method."""
        # Setup
        middleware = RedisCacheMetricsMiddleware(mock_cache)
        
        # Execute
        result = await middleware.generate_key("test", param="value")
        
        # Verify
        assert result == "test_key"
        mock_cache.generate_key.assert_awaited_once_with("test", param="value")


@patch("app.libs.redis.monitoring.RedisCacheMetricsMiddleware")
def test_create_metrics_wrapped_cache(mock_middleware_class, mock_cache):
    """Test create_metrics_wrapped_cache function."""
    # Setup
    mock_middleware = MagicMock()
    mock_middleware_class.return_value = mock_middleware
    
    # Execute
    result = create_metrics_wrapped_cache(mock_cache)
    
    # Verify
    assert result is mock_middleware
    mock_middleware_class.assert_called_once_with(mock_cache)