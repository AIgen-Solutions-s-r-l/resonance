"""
Database metrics collection.

This module provides functions and decorators for collecting
metrics related to database operations.
"""

import functools
import time
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast

from app.core.config import settings
from app.log.logging import logger
from app.metrics.core import increment_counter, report_gauge, report_timing


# Function type variable
F = TypeVar('F', bound=Callable[..., Any])


def sql_query_timer(
    query_name: str,
    tags: Optional[Dict[str, str]] = None
) -> Callable[[F], F]:
    """
    Decorator to time SQL query execution.
    
    Args:
        query_name: Name of the query
        tags: Additional tags
        
    Returns:
        Decorator function
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Skip if metrics disabled
            if not settings.metrics_enabled:
                return func(*args, **kwargs)
            
            # Create tags
            metric_tags = {
                "query": query_name
            }
            
            # Add custom tags
            if tags:
                metric_tags.update(tags)
            
            # Increment query call count
            increment_counter("db.query.calls", metric_tags)
            
            # Start timing
            start_time = time.time()
            
            try:
                # Execute function
                result = func(*args, **kwargs)
                
                # Calculate duration
                duration = time.time() - start_time
                duration_ms = duration * 1000.0
                
                # Update tags for success
                metric_tags["status"] = "success"
                
                # Report timing
                report_timing("db.query.duration", duration_ms, metric_tags)
                
                # Check for slow query
                if duration_ms > settings.slow_query_threshold_ms:
                    # Add slow query tag
                    slow_tags = metric_tags.copy()
                    slow_tags["slow"] = "true"
                    
                    # Log slow query
                    logger.warning(
                        "Slow database query detected",
                        query=query_name,
                        duration_ms=duration_ms,
                        threshold_ms=settings.slow_query_threshold_ms
                    )
                    
                    # Increment slow query counter
                    increment_counter("db.query.slow", slow_tags)
                
                # Report result size if applicable
                if result is not None and hasattr(result, "__len__"):
                    try:
                        result_size = len(result)
                        report_gauge("db.query.result_size", result_size, metric_tags)
                    except (TypeError, ValueError):
                        pass
                
                return result
                
            except Exception as e:
                # Calculate duration
                duration = time.time() - start_time
                duration_ms = duration * 1000.0
                
                # Update tags for error
                metric_tags["status"] = "error"
                metric_tags["error_type"] = e.__class__.__name__
                
                # Report timing with error tags
                report_timing("db.query.duration", duration_ms, metric_tags)
                
                # Increment error counter
                increment_counter("db.query.error", metric_tags)
                
                # Re-raise the exception
                raise
                
        return cast(F, wrapper)
    return decorator


def async_sql_query_timer(
    query_name: str,
    tags: Optional[Dict[str, str]] = None
) -> Callable[[F], F]:
    """
    Decorator to time async SQL query execution.
    
    Args:
        query_name: Name of the query
        tags: Additional tags
        
    Returns:
        Decorator function
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Skip if metrics disabled
            if not settings.metrics_enabled:
                return await func(*args, **kwargs)
            
            # Create tags
            metric_tags = {
                "query": query_name
            }
            
            # Add custom tags
            if tags:
                metric_tags.update(tags)
            
            # Increment query call count
            increment_counter("db.query.calls", metric_tags)
            
            # Start timing
            start_time = time.time()
            
            try:
                # Execute function
                result = await func(*args, **kwargs)
                
                # Calculate duration
                duration = time.time() - start_time
                duration_ms = duration * 1000.0
                
                # Update tags for success
                metric_tags["status"] = "success"
                
                # Report timing
                report_timing("db.query.duration", duration_ms, metric_tags)
                
                # Check for slow query
                if duration_ms > settings.slow_query_threshold_ms:
                    # Add slow query tag
                    slow_tags = metric_tags.copy()
                    slow_tags["slow"] = "true"
                    
                    # Log slow query
                    logger.warning(
                        "Slow database query detected",
                        query=query_name,
                        duration_ms=duration_ms,
                        threshold_ms=settings.slow_query_threshold_ms
                    )
                    
                    # Increment slow query counter
                    increment_counter("db.query.slow", slow_tags)
                
                # Report result size if applicable
                if result is not None and hasattr(result, "__len__"):
                    try:
                        result_size = len(result)
                        report_gauge("db.query.result_size", result_size, metric_tags)
                    except (TypeError, ValueError):
                        pass
                
                return result
                
            except Exception as e:
                # Calculate duration
                duration = time.time() - start_time
                duration_ms = duration * 1000.0
                
                # Update tags for error
                metric_tags["status"] = "error"
                metric_tags["error_type"] = e.__class__.__name__
                
                # Report timing with error tags
                report_timing("db.query.duration", duration_ms, metric_tags)
                
                # Increment error counter
                increment_counter("db.query.error", metric_tags)
                
                # Re-raise the exception
                raise
                
        return cast(F, wrapper)
    return decorator


def report_connection_pool_metrics(
    pool_name: str,
    used_connections: int,
    total_connections: int,
    tags: Optional[Dict[str, str]] = None
) -> None:
    """
    Report connection pool metrics.
    
    Args:
        pool_name: Name of the connection pool
        used_connections: Number of used connections
        total_connections: Total number of connections
        tags: Additional tags
    """
    if not settings.metrics_enabled:
        return
    
    try:
        # Create tags
        metric_tags = {
            "pool": pool_name
        }
        
        # Add custom tags
        if tags:
            metric_tags.update(tags)
        
        # Report connection metrics
        report_gauge("db.pool.connections.used", used_connections, metric_tags)
        report_gauge("db.pool.connections.total", total_connections, metric_tags)
        
        # Calculate and report utilization
        if total_connections > 0:
            utilization = (used_connections / total_connections) * 100.0
            report_gauge("db.pool.utilization", utilization, metric_tags)
        
    except Exception as e:
        if settings.metrics_debug:
            logger.error(
                "Failed to report connection pool metrics",
                error=str(e)
            )


def track_connection_acquisition(
    pool_name: str,
    tags: Optional[Dict[str, str]] = None
) -> Callable[[F], F]:
    """
    Decorator to track connection acquisition time.
    
    Args:
        pool_name: Name of the connection pool
        tags: Additional tags
        
    Returns:
        Decorator function
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Skip if metrics disabled
            if not settings.metrics_enabled:
                return func(*args, **kwargs)
            
            # Create tags
            metric_tags = {
                "pool": pool_name
            }
            
            # Add custom tags
            if tags:
                metric_tags.update(tags)
            
            # Start timing
            start_time = time.time()
            
            try:
                # Execute function
                result = func(*args, **kwargs)
                
                # Calculate duration
                duration = time.time() - start_time
                duration_ms = duration * 1000.0
                
                # Report timing
                report_timing("db.pool.connection_acquisition", duration_ms, metric_tags)
                
                return result
                
            except Exception as e:
                # Calculate duration
                duration = time.time() - start_time
                duration_ms = duration * 1000.0
                
                # Update tags for error
                metric_tags["status"] = "error"
                metric_tags["error_type"] = e.__class__.__name__
                
                # Report timing with error tags
                report_timing("db.pool.connection_acquisition", duration_ms, metric_tags)
                
                # Increment error counter
                increment_counter("db.pool.connection_error", metric_tags)
                
                # Re-raise the exception
                raise
                
        return cast(F, wrapper)
    return decorator


def async_track_connection_acquisition(
    pool_name: str,
    tags: Optional[Dict[str, str]] = None
) -> Callable[[F], F]:
    """
    Decorator to track async connection acquisition time.
    
    Args:
        pool_name: Name of the connection pool
        tags: Additional tags
        
    Returns:
        Decorator function
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Skip if metrics disabled
            if not settings.metrics_enabled:
                return await func(*args, **kwargs)
            
            # Create tags
            metric_tags = {
                "pool": pool_name
            }
            
            # Add custom tags
            if tags:
                metric_tags.update(tags)
            
            # Start timing
            start_time = time.time()
            
            try:
                # Execute function
                result = await func(*args, **kwargs)
                
                # Calculate duration
                duration = time.time() - start_time
                duration_ms = duration * 1000.0
                
                # Report timing
                report_timing("db.pool.connection_acquisition", duration_ms, metric_tags)
                
                return result
                
            except Exception as e:
                # Calculate duration
                duration = time.time() - start_time
                duration_ms = duration * 1000.0
                
                # Update tags for error
                metric_tags["status"] = "error"
                metric_tags["error_type"] = e.__class__.__name__
                
                # Report timing with error tags
                report_timing("db.pool.connection_acquisition", duration_ms, metric_tags)
                
                # Increment error counter
                increment_counter("db.pool.connection_error", metric_tags)
                
                # Re-raise the exception
                raise
                
        return cast(F, wrapper)
    return decorator


def report_query_plan_metrics(
    query_name: str,
    plan_data: Dict[str, Any],
    tags: Optional[Dict[str, str]] = None
) -> None:
    """
    Report metrics from PostgreSQL query plan.
    
    Args:
        query_name: Name of the query
        plan_data: Query plan data from EXPLAIN ANALYZE
        tags: Additional tags
    """
    if not settings.metrics_enabled:
        return
    
    try:
        # Create tags
        metric_tags = {
            "query": query_name
        }
        
        # Add custom tags
        if tags:
            metric_tags.update(tags)
        
        # Extract metrics from plan data
        # This is a simplified example - real implementation would parse the EXPLAIN ANALYZE output
        if "execution_time" in plan_data:
            report_gauge("db.query.plan.execution_time", plan_data["execution_time"], metric_tags)
            
        if "planning_time" in plan_data:
            report_gauge("db.query.plan.planning_time", plan_data["planning_time"], metric_tags)
            
        if "rows" in plan_data:
            report_gauge("db.query.plan.rows", plan_data["rows"], metric_tags)
        
    except Exception as e:
        if settings.metrics_debug:
            logger.error(
                "Failed to report query plan metrics",
                error=str(e)
            )