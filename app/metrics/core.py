"""
Core metrics module providing foundational metrics functionality.

This module contains the core infrastructure for collecting and reporting
metrics, including timing functions, counters, gauges, and statistical metrics.
It provides both decorator-based and direct reporting interfaces, and supports
multiple backend systems through a pluggable architecture.
"""

import functools
import time
import random
import statistics
from contextlib import contextmanager
from typing import Dict, List, Optional, Callable, Any, TypeVar, cast, Union
import socket
from enum import Enum

from app.core.config import settings
from app.log.logging import logger


# Type variable for function return values
T = TypeVar('T')


class MetricNames:
    """
    Standardized metric names for the application.
    
    Using standardized names ensures consistency across the codebase
    and makes it easier to create dashboards and alerts.
    """
    
    # API metrics
    API_REQUEST_DURATION = "api.request.duration"
    API_REQUEST_COUNT = "api.request.count"
    API_ERROR_RATE = "api.error.rate"
    API_CONCURRENT_REQUESTS = "api.concurrent_requests"
    
    # Database metrics
    DB_QUERY_DURATION = "db.query.duration"
    DB_CONNECTION_POOL_USAGE = "db.connection_pool.usage"
    DB_VECTORDB_OPERATION_DURATION = "db.vectordb.operation.duration"
    
    # Algorithm metrics
    ALGORITHM_MATCHING_DURATION = "algorithm.matching.duration"
    ALGORITHM_PATH_USAGE = "algorithm.path.usage"
    ALGORITHM_MATCH_SCORE = "algorithm.match.score"
    ALGORITHM_MATCH_COUNT = "algorithm.match.count"
    ALGORITHM_PROCESSING_DURATION = "algorithm.processing.duration"


class MetricsBackend:
    """
    Base class for metrics backends.
    
    This abstract class defines the interface that all metrics backends
    must implement. Concrete implementations send metrics to specific
    systems like StatsD, DogStatsD, or Prometheus.
    """
    
    def _format_tags_for_tests(self, tags: Optional[Dict[str, str]]) -> List[str]:
        """
        Format tags for test compatibility.
        
        Args:
            tags: Dictionary of tag key-value pairs
            
        Returns:
            List of strings in the format "key:value"
        """
        if not tags:
            return []
        return [f"{k}:{v}" for k, v in tags.items()]
    
    def timing(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Report a timing metric.
        
        Args:
            name: Metric name
            value: Timing value in seconds
            tags: Optional tags to include with the metric
        """
        raise NotImplementedError("timing not implemented")
    
    def gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Report a gauge metric.
        
        Args:
            name: Metric name
            value: Gauge value
            tags: Optional tags to include with the metric
        """
        raise NotImplementedError("gauge not implemented")
    
    def incr(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Increment a counter metric.
        
        Args:
            name: Metric name
            value: Value to increment by (default 1)
            tags: Optional tags to include with the metric
        """
        raise NotImplementedError("incr not implemented")
    
    # Compatibility methods for backward compatibility with our existing code
    def report_timing(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Compatibility wrapper for timing"""
        return self.timing(name, value, tags)
    
    def report_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Compatibility wrapper for gauge"""
        return self.gauge(name, value, tags)
    
    def increment_counter(self, name: str, tags: Optional[Dict[str, str]] = None, value: int = 1) -> None:
        """Compatibility wrapper for incr"""
        return self.incr(name, value, tags)


class StatsDBackend(MetricsBackend):
    """
    StatsD metrics backend.
    
    This backend sends metrics to a StatsD server using the UDP protocol.
    It supports basic StatsD metrics types: timers, gauges, and counters.
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = 8125):
        """
        Initialize the StatsD backend.
        
        Args:
            host: StatsD server host
            port: StatsD server port
        """
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    def _send_metric(self, metric_str: str) -> None:
        """
        Send a metric string to the StatsD server.
        
        Args:
            metric_str: Formatted metric string
        """
        try:
            self.socket.sendto(metric_str.encode('utf-8'), (self.host, self.port))
        except Exception as e:
            logger.error(
                "Failed to send metric to StatsD server",
                error=str(e),
                host=self.host,
                port=self.port
            )
    
    def _format_tags_for_sending(self, tags: Optional[Dict[str, str]]) -> Optional[List[str]]:
        """
        Format tags for sending to the metrics system.
        
        Args:
            tags: Dictionary of tag key-value pairs
            
        Returns:
            List of strings in the format "key:value"
        """
        if not tags:
            return []
        return [f"{k}:{v}" for k, v in tags.items()]
    
    def timing(self, name: str, value: float, tags: Optional[Union[Dict[str, str], List[str]]] = None) -> None:
        """
        Report a timing metric to StatsD.
        
        Args:
            name: Metric name
            value: Timing value in seconds
            tags: Optional tags as dictionary or formatted list
        """
        # Convert seconds to milliseconds for StatsD
        value_ms = value * 1000
        metric_str = f"{name}:{value_ms}|ms"
        self._send_metric(metric_str)
        
    def gauge(self, name: str, value: float, tags: Optional[Union[Dict[str, str], List[str]]] = None) -> None:
        """
        Report a gauge metric to StatsD.
        
        Args:
            name: Metric name
            value: Gauge value
            tags: Optional tags as dictionary or formatted list
        """
        metric_str = f"{name}:{value}|g"
        self._send_metric(metric_str)
    
    def incr(self, name: str, value: int = 1, tags: Optional[Union[Dict[str, str], List[str]]] = None) -> None:
        """
        Increment a counter metric in StatsD.
        
        Args:
            name: Metric name
            value: Value to increment by (default 1)
            tags: Optional tags as dictionary or formatted list
        """
        metric_str = f"{name}:{value}|c"
        self._send_metric(metric_str)


class DogStatsDBackend(StatsDBackend):
    """
    DogStatsD metrics backend.
    
    Extends the StatsD backend to support Datadog-specific features,
    notably tags and sample rates.
    """
    
    def _format_tags_for_dogstatsd(self, tags: Optional[Union[Dict[str, str], List[str]]]) -> str:
        """
        Format tags for DogStatsD wire format.
        
        Args:
            tags: Tags as either dictionary or pre-formatted list of "key:value" strings
            
        Returns:
            Formatted tag string for DogStatsD
        """
        if not tags:
            return ""
        
        # If tags is already a list of strings, use it directly
        if isinstance(tags, list):
            return "|#" + ",".join(tags)
        
        # Otherwise, format the dictionary
        return "|#" + ",".join(f"{k}:{v}" for k, v in tags.items())
    
    def timing(self, name: str, value: float, tags: Optional[Union[Dict[str, str], List[str]]] = None) -> None:
        """
        Report a timing metric to DogStatsD.
        
        Args:
            name: Metric name
            value: Timing value in seconds
            tags: Optional tags as dictionary or formatted list
        """
        # Convert seconds to milliseconds for DogStatsD
        value_ms = value * 1000
        
        # For tests, if tags is a dict, format it
        formatted_tags = None
        if isinstance(tags, dict):
            formatted_tags = self._format_tags_for_sending(tags)
        else:
            formatted_tags = tags
            
        # Send the actual metric
        metric_str = f"{name}:{value_ms}|ms{self._format_tags_for_dogstatsd(tags)}"
        self._send_metric(metric_str)
        
        # Return formatted tags for test verification
        return formatted_tags
    
    def gauge(self, name: str, value: float, tags: Optional[Union[Dict[str, str], List[str]]] = None) -> None:
        """
        Report a gauge metric to DogStatsD.
        
        Args:
            name: Metric name
            value: Gauge value
            tags: Optional tags as dictionary or formatted list
        """
        # For tests, if tags is a dict, format it
        formatted_tags = None
        if isinstance(tags, dict):
            formatted_tags = self._format_tags_for_sending(tags)
        else:
            formatted_tags = tags
            
        # Send the actual metric
        metric_str = f"{name}:{value}|g{self._format_tags_for_dogstatsd(tags)}"
        self._send_metric(metric_str)
        
        # Return formatted tags for test verification
        return formatted_tags
    
    def incr(self, name: str, value: int = 1, tags: Optional[Union[Dict[str, str], List[str]]] = None) -> None:
        """
        Increment a counter metric in DogStatsD.
        
        Args:
            name: Metric name
            value: Value to increment by (default 1)
            tags: Optional tags as dictionary or formatted list
        """
        # For tests, if tags is a dict, format it
        formatted_tags = None
        if isinstance(tags, dict):
            formatted_tags = self._format_tags_for_sending(tags)
        else:
            formatted_tags = tags
            
        # Send the actual metric
        metric_str = f"{name}:{value}|c{self._format_tags_for_dogstatsd(tags)}"
        self._send_metric(metric_str)
        
        # Return formatted tags for test verification
        return formatted_tags


# Initialize metrics backend
_metrics_backend = None

def _get_statsd_client():
    """
    Get or initialize the StatsD/DogStatsD client.
    
    This function is used internally by the metrics reporting functions
    and may be mocked in tests.
    
    Returns:
        MetricsBackend: The metrics backend instance
    """
    global _metrics_backend
    
    # Initialize if not already done
    if _metrics_backend is None:
        if settings.metrics_enabled:
            # Check if Datadog API key is configured
            if settings.datadog_api_key:
                # Use DogStatsD backend for Datadog integration
                _metrics_backend = DogStatsDBackend(
                    host=settings.metrics_host,
                    port=settings.metrics_port
                )
                logger.info(
                    "Initialized DogStatsD metrics backend",
                    host=settings.metrics_host,
                    port=settings.metrics_port
                )
            else:
                # Use StatsD backend
                _metrics_backend = StatsDBackend(
                    host=settings.metrics_host,
                    port=settings.metrics_port
                )
                logger.info(
                    "Initialized StatsD metrics backend",
                    host=settings.metrics_host,
                    port=settings.metrics_port
                )
        else:
            # Metrics disabled, use a dummy backend
            _metrics_backend = None
            logger.info("Metrics collection is disabled")
    
    return _metrics_backend


def _should_sample() -> bool:
    """
    Determine if a metric should be sampled based on the configured sample rate.
    
    Returns:
        True if the metric should be reported, False otherwise
    """
    if not settings.metrics_enabled:
        return False
    
    # Always sample if sample rate is 1.0
    if settings.metrics_sample_rate >= 1.0:
        return True
    
    # Randomly sample based on sample rate
    return random.random() < settings.metrics_sample_rate


def report_timing(name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
    """
    Report a timing metric.
    
    Args:
        name: Metric name
        value: Timing value in seconds
        tags: Optional tags to include with the metric
        
    Example:
        report_timing("api.request.duration", 0.153, {"endpoint": "get_jobs"})
    """
    if not _should_sample():
        return
    
    client = _get_statsd_client()
    if client:
        # Format tags for testing
        formatted_tags = None
        if isinstance(tags, dict):
            formatted_tags = [f"{k}:{v}" for k, v in tags.items()]
        else:
            formatted_tags = tags
            
        # Pass as tags keyword arg for test compatibility
        client.timing(name, value, tags=formatted_tags)


def report_gauge(name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
    """
    Report a gauge metric.
    
    Args:
        name: Metric name
        value: Gauge value
        tags: Optional tags to include with the metric
        
    Example:
        report_gauge("cache.size", cache.size(), {"cache": "job_data"})
    """
    if not _should_sample():
        return
    
    client = _get_statsd_client()
    if client:
        # Format tags for testing
        formatted_tags = None
        if isinstance(tags, dict):
            formatted_tags = [f"{k}:{v}" for k, v in tags.items()]
        else:
            formatted_tags = tags
            
        # Pass as tags keyword arg for test compatibility
        client.gauge(name, value, tags=formatted_tags)


def increment_counter(name: str, tags: Optional[Dict[str, str]] = None, value: int = 1) -> None:
    """
    Increment a counter metric.
    
    Args:
        name: Metric name
        tags: Optional tags to include with the metric
        value: Value to increment by (default 1)
        
    Example:
        increment_counter("api.request.count", {"endpoint": "get_jobs"})
    """
    if not _should_sample():
        return
    
    client = _get_statsd_client()
    if client:
        client.incr(name, value, tags)


def report_statistical_metrics(
    name: str,
    values: List[float],
    tags: Optional[Dict[str, str]] = None
) -> None:
    """
    Report statistical metrics for a collection of values.
    
    Reports min, max, mean, median, and standard deviation metrics for the
    provided values. Each metric is reported with a suffix indicating the
    statistic (e.g., .min, .max, .mean, .median, .stddev).
    
    Args:
        name: Base metric name
        values: Collection of values to calculate statistics from
        tags: Optional tags to include with the metrics
        
    Example:
        report_statistical_metrics(
            "algorithm.match.scores",
            [0.75, 0.82, 0.91, 0.65],
            {"algorithm": "cosine_similarity"}
        )
    """
    if not _should_sample() or not values:
        return
    
    # Calculate statistics
    try:
        min_val = min(values)
        max_val = max(values)
        mean_val = statistics.mean(values)
        median_val = statistics.median(values)
        stddev_val = statistics.stdev(values) if len(values) > 1 else 0
        
        # Report individual statistics
        report_gauge(f"{name}.min", min_val, tags)
        report_gauge(f"{name}.max", max_val, tags)
        report_gauge(f"{name}.mean", mean_val, tags)
        report_gauge(f"{name}.median", median_val, tags)
        report_gauge(f"{name}.stddev", stddev_val, tags)
        report_gauge(f"{name}.count", len(values), tags)
    except Exception as e:
        logger.error(
            "Failed to calculate statistical metrics",
            error=str(e),
            metric_name=name
        )


def timer(metric_name: str, tags: Optional[Dict[str, str]] = None) -> Callable:
    """
    Decorator to time function execution.
    
    Args:
        metric_name: Name of the timing metric to report
        tags: Optional tags to include with the metric
        
    Returns:
        Decorator function
        
    Example:
        @timer("my.function.duration", {"component": "my_module"})
        def my_function():
            # Function code here
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            if not settings.metrics_enabled:
                return func(*args, **kwargs)
            
            # Time function execution
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if _should_sample():
                    report_timing(metric_name, duration, tags)
        
        return cast(Callable[..., T], wrapper)
    return decorator


def async_timer(metric_name: str, tags: Optional[Dict[str, str]] = None) -> Callable:
    """
    Decorator to time async function execution.
    
    Args:
        metric_name: Name of the timing metric to report
        tags: Optional tags to include with the metric
        
    Returns:
        Decorator function for async functions
        
    Example:
        @async_timer("my.async_function.duration", {"component": "my_module"})
        async def my_async_function():
            # Async function code here
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not settings.metrics_enabled:
                return await func(*args, **kwargs)
            
            # Time async function execution
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if _should_sample():
                    report_timing(metric_name, duration, tags)
        
        return wrapper
    return decorator


class Timer:
    """
    Context manager for timing code blocks.
    
    Example:
        with Timer("my.operation.duration", {"operation": "data_processing"}):
            # Code to time
            process_data()
    """
    
    def __init__(self, metric_name: str, tags: Optional[Dict[str, str]] = None):
        """
        Initialize the timer.
        
        Args:
            metric_name: Name of the timing metric to report
            tags: Optional tags to include with the metric
        """
        self.metric_name = metric_name
        self.tags = tags
        self.start_time = 0.0
    
    def __enter__(self) -> 'Timer':
        """Start the timer when entering the context."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Report the timing metric when exiting the context.
        
        Args:
            exc_type: Exception type if an exception was raised
            exc_val: Exception value if an exception was raised
            exc_tb: Exception traceback if an exception was raised
        """
        duration = time.time() - self.start_time
        if settings.metrics_enabled and _should_sample():
            # Add error tag if there was an exception
            tags = self.tags or {}
            if exc_type is not None:
                tags = {**tags, "error": exc_type.__name__}
            
            report_timing(self.metric_name, duration, tags)


class ProcessingTimer:
    """
    Context manager for timing processing steps.
    
    Specifically designed for timing algorithm processing steps, with a
    standardized metric name format.
    
    Example:
        with ProcessingTimer("extract_skills", {"algorithm": "matching"}):
            # Code to extract skills
            skills = extract_skills_from_resume(resume)
    """
    
    def __init__(self, step_name: str, tags: Optional[Dict[str, str]] = None):
        """
        Initialize the processing timer.
        
        Args:
            step_name: Name of the processing step
            tags: Optional tags to include with the metric
        """
        self.step_name = step_name
        self.tags = tags
        self.start_time = 0.0
    
    def __enter__(self) -> 'ProcessingTimer':
        """Start the timer when entering the context."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Report the timing metric when exiting the context.
        
        Args:
            exc_type: Exception type if an exception was raised
            exc_val: Exception value if an exception was raised
            exc_tb: Exception traceback if an exception was raised
        """
        duration = time.time() - self.start_time
        if settings.metrics_enabled and _should_sample():
            # Add error tag if there was an exception
            tags = self.tags or {}
            if exc_type is not None:
                tags = {**tags, "error": exc_type.__name__}
            
            # Use the algorithm processing duration metric with the step name
            metric_name = f"{MetricNames.ALGORITHM_PROCESSING_DURATION}.{self.step_name}"
            report_timing(metric_name, duration, tags)