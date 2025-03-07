"""
Tests for the metrics system.

This module contains tests for the metrics collection and reporting functionality.
"""

import pytest
import time
from unittest.mock import patch, MagicMock
from app.metrics.core import (
    Timer,
    timer,
    async_timer,
    report_timing,
    report_gauge,
    increment_counter
)
from app.metrics.algorithm import (
    matching_algorithm_timer,
    report_match_score_distribution,
    report_algorithm_path,
    report_match_count
)
from app.metrics.database import (
    sql_query_timer,
    report_connection_pool_metrics
)


@pytest.fixture
def enable_metrics():
    """Fixture to temporarily enable metrics for testing."""
    with patch('app.metrics.core.settings') as mock_settings:
        mock_settings.metrics_enabled = True
        mock_settings.metrics_sample_rate = 1.0
        yield mock_settings


@pytest.fixture
def disable_metrics():
    """Fixture to temporarily disable metrics for testing."""
    with patch('app.metrics.core.settings') as mock_settings:
        mock_settings.metrics_enabled = False
        yield mock_settings


@pytest.fixture
def mock_statsd_client():
    """Fixture to mock the statsd client."""
    with patch('app.metrics.core._get_statsd_client') as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        yield mock_client


def test_timer_context_manager(enable_metrics, mock_statsd_client):
    """Test the Timer context manager."""
    with Timer("test.duration", {"test": "context_manager"}):
        time.sleep(0.001)  # Simulate work
    
    # Verify the timing metric was reported
    mock_statsd_client.timing.assert_called_once()
    # Get the arguments of the call
    args, kwargs = mock_statsd_client.timing.call_args
    
    # Check the metric name
    assert args[0] == "test.duration"
    # Check that the value is positive (time elapsed)
    assert args[1] > 0
    # Check the tags contain our test tag
    assert "test:context_manager" in kwargs.get("tags", [])


@timer("test.function", {"test": "decorator"})
def sample_timed_function():
    """Sample function to test the timer decorator."""
    time.sleep(0.001)  # Simulate work
    return "result"


def test_timer_decorator(enable_metrics, mock_statsd_client):
    """Test the timer decorator."""
    result = sample_timed_function()
    
    # Verify the function returned the expected result
    assert result == "result"
    
    # Verify the timing metric was reported
    mock_statsd_client.timing.assert_called_once()
    args, kwargs = mock_statsd_client.timing.call_args
    
    # Check the metric name
    assert args[0] == "test.function"
    # Check that the value is positive (time elapsed)
    assert args[1] > 0
    # Check the tags contain our test tag
    assert "test:decorator" in kwargs.get("tags", [])


@matching_algorithm_timer("test_algorithm")
def sample_algorithm_function():
    """Sample function to test the algorithm timer decorator."""
    time.sleep(0.001)  # Simulate work
    return "algorithm result"


def test_algorithm_timer(enable_metrics, mock_statsd_client):
    """Test the algorithm timer decorator."""
    result = sample_algorithm_function()
    
    # Verify the function returned the expected result
    assert result == "algorithm result"
    
    # Verify the timing metric was reported
    mock_statsd_client.timing.assert_called_once()
    args, kwargs = mock_statsd_client.timing.call_args
    
    # Check the metric name and algorithm tag
    assert args[0] == "algorithm.matching.duration"
    assert "algorithm:test_algorithm" in kwargs.get("tags", [])


def test_report_match_score_distribution(enable_metrics, mock_statsd_client):
    """Test reporting match score distribution."""
    scores = [0.75, 0.80, 0.85, 0.90, 0.95]
    report_match_score_distribution(scores, {"test": "distribution"})
    
    # Verify multiple gauge reports were made (mean, min, max, etc.)
    assert mock_statsd_client.gauge.call_count >= 5
    
    # Check at least one call had our test tag
    found_test_tag = False
    for call in mock_statsd_client.gauge.call_args_list:
        args, kwargs = call
        if "test:distribution" in kwargs.get("tags", []):
            found_test_tag = True
            break
    
    assert found_test_tag, "Test tag not found in any gauge calls"


def test_metrics_disabled(disable_metrics, mock_statsd_client):
    """Test that metrics are not reported when disabled."""
    # Try to report metrics with metrics disabled
    report_timing("test.disabled", 0.1, {"test": "disabled"})
    report_gauge("test.disabled", 42, {"test": "disabled"})
    increment_counter("test.disabled", {"test": "disabled"})
    
    # Verify no metrics were reported
    mock_statsd_client.timing.assert_not_called()
    mock_statsd_client.gauge.assert_not_called()
    mock_statsd_client.incr.assert_not_called()


def test_algorithm_path_reporting(enable_metrics, mock_statsd_client):
    """Test reporting algorithm path usage."""
    report_algorithm_path("vector_similarity", {"reason": "test"})
    
    # Verify the counter was incremented
    mock_statsd_client.incr.assert_called_once()
    args, kwargs = mock_statsd_client.incr.call_args
    
    # Check for expected tags
    assert "path:vector_similarity" in kwargs.get("tags", [])
    assert "reason:test" in kwargs.get("tags", [])


def test_match_count_reporting(enable_metrics, mock_statsd_client):
    """Test reporting match count."""
    report_match_count(42, {"source": "test"})
    
    # Verify the gauge was set
    mock_statsd_client.gauge.assert_called_once()
    args, kwargs = mock_statsd_client.gauge.call_args
    
    # Check metric name and value
    assert args[0] == "algorithm.match.count"
    assert args[1] == 42
    # Check tags
    assert "source:test" in kwargs.get("tags", [])


def test_connection_pool_metrics(enable_metrics, mock_statsd_client):
    """Test reporting connection pool metrics."""
    report_connection_pool_metrics("test_pool", 5, 10)
    
    # Verify multiple gauge calls for used, total, and percentage
    assert mock_statsd_client.gauge.call_count >= 3
    
    # Check for pool tag in all calls
    all_calls_have_pool_tag = True
    for call in mock_statsd_client.gauge.call_args_list:
        args, kwargs = call
        if "pool:test_pool" not in kwargs.get("tags", []):
            all_calls_have_pool_tag = False
            break
    
    assert all_calls_have_pool_tag, "Pool tag missing from some gauge calls"