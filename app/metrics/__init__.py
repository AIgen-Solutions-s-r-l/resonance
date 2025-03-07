"""
Metrics collection package.

This package provides functionality for collecting and reporting metrics
for various aspects of the application.
"""

from typing import Any, Dict, Optional, Union

# Import core metrics functionality
from app.metrics.core import (
    initialize_metrics,
    increment_counter,
    report_gauge,
    report_timing,
    report_histogram,
    get_all_backends
)

# Import metrics middleware
from app.metrics.middleware import (
    MetricsMiddleware,
    add_metrics_middleware,
    add_timing_header_middleware,
    setup_all_middleware
)

# Import backend setup
from app.metrics.backends.prometheus import setup_metrics_endpoint

# Import system metrics
from app.metrics.system import collect_system_metrics

# Import metrics collection tasks
from app.metrics.tasks import (
    start_metrics_collection,
    stop_metrics_collection,
    register_collection_task,
    unregister_collection_task,
    get_task_status
)

# Import database metrics
from app.metrics.database import (
    track_query,
    track_async_query,
    report_connection_pool_stats,
    report_query_error,
    collect_mongodb_stats
)

# Import algorithm metrics
from app.metrics.algorithm import (
    matching_algorithm_timer,
    async_matching_algorithm_timer,
    report_match_score_distribution,
    report_algorithm_path,
    report_match_count,
    instrument_job_matcher,
    track_match_operation,
    track_async_match_operation
)


def setup_metrics(app: Any) -> None:
    """
    Set up metrics for a FastAPI application.
    
    This function initializes metrics, sets up middleware, and starts
    the metrics collection thread.
    
    Args:
        app: FastAPI application
    """
    from app.core.config import settings
    from app.log.logging import logger
    
    if not settings.metrics_enabled:
        logger.info("Metrics collection is disabled")
        return
    
    try:
        # Initialize metrics
        initialize_metrics()
        
        # Set up middleware
        setup_all_middleware(app)
        
        # Set up Prometheus endpoint if enabled
        if settings.metrics_prometheus_enabled:
            setup_metrics_endpoint(app)
        
        # Start metrics collection thread
        if settings.metrics_collection_enabled:
            start_metrics_collection()
        
        logger.info(
            "Metrics setup complete",
            enabled=settings.metrics_enabled,
            statsd_enabled=settings.metrics_statsd_enabled,
            prometheus_enabled=settings.metrics_prometheus_enabled,
            collection_enabled=settings.metrics_collection_enabled
        )
        
    except Exception as e:
        logger.error(
            "Failed to set up metrics",
            error=str(e)
        )


def get_default_tags() -> Dict[str, str]:
    """
    Get default tags for metrics.
    
    Returns:
        Dictionary of default tags
    """
    from app.core.config import settings
    
    tags = {}
    
    # Add environment tag
    if settings.metrics_environment:
        tags["env"] = settings.metrics_environment
    
    # Add application name tag
    app_name = settings.metrics_app_name or settings.app_name
    if app_name:
        tags["app"] = app_name
    
    return tags


# Aliases for backward compatibility
init_app = setup_metrics

# Re-export commonly used functions with simpler names
def increment(
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
    increment_counter(name, tags, value)


def gauge(
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
    report_gauge(name, value, tags)


def timing(
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
    report_timing(name, value, tags)


def histogram(
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
    report_histogram(name, value, tags)


# Decorators re-exported with simpler names
timer = matching_algorithm_timer
async_timer = async_matching_algorithm_timer
query_timer = track_query
async_query_timer = track_async_query