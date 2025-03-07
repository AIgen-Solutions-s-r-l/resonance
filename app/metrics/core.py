"""
Core metrics functionality.

This module provides the foundation for collecting and reporting metrics
with support for multiple backends (StatsD, Prometheus).
"""

import time
from threading import Lock
from typing import Any, Dict, List, Optional, Union, cast

from app.core.config import settings
from app.log.logging import logger


# Backend registry
_backends: List[Any] = []
_backends_lock = Lock()

# Initialization flag
_initialized = False
_init_lock = Lock()


def initialize_metrics() -> bool:
    """
    Initialize the metrics system.
    
    This function sets up the metrics backends based on configuration.
    
    Returns:
        True if initialization was successful, False otherwise
    """
    global _initialized
    
    # Skip if metrics disabled or already initialized
    if not settings.metrics_enabled:
        return False
    
    # Prevent concurrent initialization
    with _init_lock:
        if _initialized:
            logger.debug("Metrics system already initialized")
            return True
        
        try:
            logger.info("Initializing metrics system")
            
            # Initialize StatsD backend if enabled
            if settings.metrics_statsd_enabled:
                try:
                    from app.metrics.backends.statsd import StatsDBackend
                    
                    backend = StatsDBackend(
                        host=settings.metrics_statsd_host,
                        port=settings.metrics_statsd_port,
                        prefix=settings.metrics_prefix,
                        sample_rate=settings.metrics_sample_rate
                    )
                    
                    register_backend(backend)
                    
                    logger.info(
                        "StatsD metrics backend initialized",
                        host=settings.metrics_statsd_host,
                        port=settings.metrics_statsd_port
                    )
                    
                except ImportError:
                    logger.warning("Could not import StatsD backend, skipping")
                except Exception as e:
                    logger.error(
                        "Failed to initialize StatsD backend",
                        error=str(e)
                    )
            
            # Initialize Prometheus backend if enabled
            if settings.metrics_prometheus_enabled:
                try:
                    from app.metrics.backends.prometheus import PrometheusBackend
                    
                    backend = PrometheusBackend(
                        prefix=settings.metrics_prefix
                    )
                    
                    register_backend(backend)
                    
                    logger.info("Prometheus metrics backend initialized")
                    
                except ImportError:
                    logger.warning("Could not import Prometheus backend, skipping")
                except Exception as e:
                    logger.error(
                        "Failed to initialize Prometheus backend",
                        error=str(e)
                    )
            
            # Set initialization flag
            _initialized = True
            
            logger.info(
                "Metrics system initialized",
                backends_count=len(_backends)
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to initialize metrics system",
                error=str(e)
            )
            return False


def register_backend(backend: Any) -> None:
    """
    Register a metrics backend.
    
    Args:
        backend: Metrics backend instance
    """
    with _backends_lock:
        _backends.append(backend)


def get_all_backends() -> List[Any]:
    """
    Get all registered metrics backends.
    
    Returns:
        List of metrics backends
    """
    with _backends_lock:
        return list(_backends)


def get_default_tags() -> Dict[str, str]:
    """
    Get default tags for metrics.
    
    Returns:
        Dictionary of default tags
    """
    tags = {}
    
    # Add environment tag
    if settings.metrics_environment:
        tags["env"] = settings.metrics_environment
    
    # Add application name tag
    app_name = settings.metrics_app_name or settings.app_name
    if app_name:
        tags["app"] = app_name
    
    return tags


def increment_counter(
    name: str,
    tags: Optional[Dict[str, str]] = None,
    value: int = 1
) -> None:
    """
    Increment a counter metric.
    
    Args:
        name: Metric name
        tags: Optional tags
        value: Value to increment by
    """
    if not settings.metrics_enabled or not _initialized:
        return
    
    try:
        # Combine default tags with provided tags
        all_tags = get_default_tags()
        if tags:
            all_tags.update(tags)
        
        # Report to all backends
        with _backends_lock:
            for backend in _backends:
                try:
                    backend.increment(name, all_tags, value)
                except Exception as e:
                    if settings.metrics_debug:
                        logger.error(
                            "Failed to increment counter",
                            backend=backend.__class__.__name__,
                            metric=name,
                            error=str(e)
                        )
    
    except Exception as e:
        if settings.metrics_debug:
            logger.error(
                "Failed to increment counter",
                metric=name,
                error=str(e)
            )


def report_gauge(
    name: str,
    value: Union[int, float],
    tags: Optional[Dict[str, str]] = None
) -> None:
    """
    Report a gauge metric.
    
    Args:
        name: Metric name
        value: Gauge value
        tags: Optional tags
    """
    if not settings.metrics_enabled or not _initialized:
        return
    
    try:
        # Combine default tags with provided tags
        all_tags = get_default_tags()
        if tags:
            all_tags.update(tags)
        
        # Report to all backends
        with _backends_lock:
            for backend in _backends:
                try:
                    backend.gauge(name, value, all_tags)
                except Exception as e:
                    if settings.metrics_debug:
                        logger.error(
                            "Failed to report gauge",
                            backend=backend.__class__.__name__,
                            metric=name,
                            error=str(e)
                        )
    
    except Exception as e:
        if settings.metrics_debug:
            logger.error(
                "Failed to report gauge",
                metric=name,
                error=str(e)
            )


def report_timing(
    name: str,
    value: float,
    tags: Optional[Dict[str, str]] = None
) -> None:
    """
    Report a timing metric.
    
    Args:
        name: Metric name
        value: Timing value in milliseconds
        tags: Optional tags
    """
    if not settings.metrics_enabled or not _initialized:
        return
    
    try:
        # Check if timing is slow
        if name.endswith(".duration") and value > settings.slow_request_threshold_ms:
            slow_tags = tags.copy() if tags else {}
            slow_tags["slow"] = "true"
            slow_tags["threshold_ms"] = str(settings.slow_request_threshold_ms)
            
            # Log slow timing
            logger.warning(
                "Slow operation detected",
                metric=name,
                duration_ms=value,
                threshold_ms=settings.slow_request_threshold_ms,
                **slow_tags
            )
        
        # Combine default tags with provided tags
        all_tags = get_default_tags()
        if tags:
            all_tags.update(tags)
        
        # Report to all backends
        with _backends_lock:
            for backend in _backends:
                try:
                    backend.timing(name, value, all_tags)
                except Exception as e:
                    if settings.metrics_debug:
                        logger.error(
                            "Failed to report timing",
                            backend=backend.__class__.__name__,
                            metric=name,
                            error=str(e)
                        )
    
    except Exception as e:
        if settings.metrics_debug:
            logger.error(
                "Failed to report timing",
                metric=name,
                error=str(e)
            )


def report_histogram(
    name: str,
    value: Union[int, float],
    tags: Optional[Dict[str, str]] = None
) -> None:
    """
    Report a histogram metric.
    
    Args:
        name: Metric name
        value: Histogram value
        tags: Optional tags
    """
    if not settings.metrics_enabled or not _initialized:
        return
    
    try:
        # Combine default tags with provided tags
        all_tags = get_default_tags()
        if tags:
            all_tags.update(tags)
        
        # Report to all backends
        with _backends_lock:
            for backend in _backends:
                try:
                    # Not all backends support histograms
                    if hasattr(backend, "histogram"):
                        backend.histogram(name, value, all_tags)
                    else:
                        # Fall back to gauge for backends without histogram support
                        backend.gauge(name, value, all_tags)
                except Exception as e:
                    if settings.metrics_debug:
                        logger.error(
                            "Failed to report histogram",
                            backend=backend.__class__.__name__,
                            metric=name,
                            error=str(e)
                        )
    
    except Exception as e:
        if settings.metrics_debug:
            logger.error(
                "Failed to report histogram",
                metric=name,
                error=str(e)
            )


class Timer:
    """Timer context manager for measuring durations."""
    
    def __init__(
        self,
        name: str,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Initialize a timer.
        
        Args:
            name: Metric name
            tags: Optional tags
        """
        self.name = name
        self.tags = tags
        self.start_time = 0.0
    
    def __enter__(self) -> "Timer":
        """
        Start timing.
        
        Returns:
            Self for context manager
        """
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Stop timing and report metric.
        
        Args:
            exc_type: Exception type
            exc_val: Exception value
            exc_tb: Exception traceback
        """
        # Calculate duration
        duration = time.time() - self.start_time
        duration_ms = duration * 1000.0
        
        # Update tags based on exception
        tags = self.tags.copy() if self.tags else {}
        if exc_type is not None:
            tags["error"] = "true"
            tags["error_type"] = exc_type.__name__
        
        # Report timing
        report_timing(self.name, duration_ms, tags)


def timer(name: str, tags: Optional[Dict[str, str]] = None) -> Timer:
    """
    Create a timer context manager.
    
    Args:
        name: Metric name
        tags: Optional tags
        
    Returns:
        Timer context manager
    """
    return Timer(name, tags)