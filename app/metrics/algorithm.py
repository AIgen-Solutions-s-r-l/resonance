"""
Algorithm metrics collection.

This module provides functions and decorators for collecting metrics
related to matching algorithms, their performance, and results.
"""

import functools
import statistics
import time
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast

from app.core.config import settings
from app.log.logging import logger
from app.metrics.core import increment_counter, report_gauge, report_histogram, report_timing


# Function type variable
F = TypeVar('F', bound=Callable[..., Any])


def matching_algorithm_timer(
    algorithm_name: str,
    tags: Optional[Dict[str, str]] = None
) -> Callable[[F], F]:
    """
    Decorator to time a matching algorithm function.
    
    Args:
        algorithm_name: Name of the algorithm
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
                "algorithm": algorithm_name
            }
            
            # Add custom tags
            if tags:
                metric_tags.update(tags)
            
            # Increment algorithm call count
            increment_counter("algorithm.calls", metric_tags)
            
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
                report_timing("algorithm.duration", duration_ms, metric_tags)
                
                # Report result size if applicable
                if result is not None and hasattr(result, "__len__"):
                    try:
                        result_size = len(result)
                        report_gauge("algorithm.result_size", result_size, metric_tags)
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
                report_timing("algorithm.duration", duration_ms, metric_tags)
                
                # Increment error counter
                increment_counter("algorithm.error_count", metric_tags)
                
                # Re-raise the exception
                raise
                
        return cast(F, wrapper)
    return decorator


def async_matching_algorithm_timer(
    algorithm_name: str,
    tags: Optional[Dict[str, str]] = None
) -> Callable[[F], F]:
    """
    Decorator to time an async matching algorithm function.
    
    Args:
        algorithm_name: Name of the algorithm
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
                "algorithm": algorithm_name
            }
            
            # Add custom tags
            if tags:
                metric_tags.update(tags)
            
            # Increment algorithm call count
            increment_counter("algorithm.calls", metric_tags)
            
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
                report_timing("algorithm.duration", duration_ms, metric_tags)
                
                # Report result size if applicable
                if result is not None and hasattr(result, "__len__"):
                    try:
                        result_size = len(result)
                        report_gauge("algorithm.result_size", result_size, metric_tags)
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
                report_timing("algorithm.duration", duration_ms, metric_tags)
                
                # Increment error counter
                increment_counter("algorithm.error_count", metric_tags)
                
                # Re-raise the exception
                raise
                
        return cast(F, wrapper)
    return decorator


def report_algorithm_path(
    path_name: str,
    tags: Optional[Dict[str, str]] = None
) -> None:
    """
    Report that a specific algorithm path was taken.
    
    Args:
        path_name: Name of the algorithm path
        tags: Additional tags
    """
    if not settings.metrics_enabled:
        return
    
    try:
        # Create tags
        metric_tags = {
            "path": path_name
        }
        
        # Add custom tags
        if tags:
            metric_tags.update(tags)
        
        # Increment path counter
        increment_counter("algorithm.path", metric_tags)
        
    except Exception as e:
        if settings.metrics_debug:
            logger.error(
                "Failed to report algorithm path",
                error=str(e)
            )


def report_match_count(
    count: int,
    tags: Optional[Dict[str, str]] = None
) -> None:
    """
    Report the number of matches found.
    
    Args:
        count: Number of matches
        tags: Additional tags
    """
    if not settings.metrics_enabled:
        return
    
    try:
        # Create tags
        metric_tags = {}
        
        # Add custom tags
        if tags:
            metric_tags.update(tags)
        
        # Report match count
        report_gauge("algorithm.match_count", count, metric_tags)
        
    except Exception as e:
        if settings.metrics_debug:
            logger.error(
                "Failed to report match count",
                error=str(e)
            )


def report_match_score_distribution(
    scores: List[float],
    tags: Optional[Dict[str, str]] = None
) -> None:
    """
    Report statistics about match score distribution.
    
    Args:
        scores: List of match scores
        tags: Additional tags
    """
    if not settings.metrics_enabled or not scores:
        return
    
    try:
        # Create tags
        metric_tags = {}
        
        # Add custom tags
        if tags:
            metric_tags.update(tags)
        
        # Report score metrics
        report_gauge("algorithm.score.min", min(scores), metric_tags)
        report_gauge("algorithm.score.max", max(scores), metric_tags)
        report_gauge("algorithm.score.mean", statistics.mean(scores), metric_tags)
        
        if len(scores) > 1:
            report_gauge("algorithm.score.median", statistics.median(scores), metric_tags)
            report_gauge("algorithm.score.stdev", statistics.stdev(scores), metric_tags)
        
        # Report histogram of scores
        for score in scores:
            report_histogram("algorithm.score.distribution", score, metric_tags)
        
    except Exception as e:
        if settings.metrics_debug:
            logger.error(
                "Failed to report match score distribution",
                error=str(e)
            )


def track_match_operation(
    operation_name: str,
    tags: Optional[Dict[str, str]] = None
) -> Callable[[F], F]:
    """
    Decorator to track a matching operation.
    
    Args:
        operation_name: Name of the operation
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
                "operation": operation_name
            }
            
            # Add custom tags
            if tags:
                metric_tags.update(tags)
            
            # Increment operation call count
            increment_counter("algorithm.operation.calls", metric_tags)
            
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
                report_timing("algorithm.operation.duration", duration_ms, metric_tags)
                
                return result
                
            except Exception as e:
                # Calculate duration
                duration = time.time() - start_time
                duration_ms = duration * 1000.0
                
                # Update tags for error
                metric_tags["status"] = "error"
                metric_tags["error_type"] = e.__class__.__name__
                
                # Report timing with error tags
                report_timing("algorithm.operation.duration", duration_ms, metric_tags)
                
                # Increment error counter
                increment_counter("algorithm.operation.error_count", metric_tags)
                
                # Re-raise the exception
                raise
                
        return cast(F, wrapper)
    return decorator


def track_async_match_operation(
    operation_name: str,
    tags: Optional[Dict[str, str]] = None
) -> Callable[[F], F]:
    """
    Decorator to track an async matching operation.
    
    Args:
        operation_name: Name of the operation
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
                "operation": operation_name
            }
            
            # Add custom tags
            if tags:
                metric_tags.update(tags)
            
            # Increment operation call count
            increment_counter("algorithm.operation.calls", metric_tags)
            
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
                report_timing("algorithm.operation.duration", duration_ms, metric_tags)
                
                return result
                
            except Exception as e:
                # Calculate duration
                duration = time.time() - start_time
                duration_ms = duration * 1000.0
                
                # Update tags for error
                metric_tags["status"] = "error"
                metric_tags["error_type"] = e.__class__.__name__
                
                # Report timing with error tags
                report_timing("algorithm.operation.duration", duration_ms, metric_tags)
                
                # Increment error counter
                increment_counter("algorithm.operation.error_count", metric_tags)
                
                # Re-raise the exception
                raise
                
        return cast(F, wrapper)
    return decorator


def instrument_job_matcher(job_matcher: Any) -> None:
    """
    Instrument a JobMatcher instance with additional metrics collection.
    
    Args:
        job_matcher: JobMatcher instance to instrument
    """
    if not settings.metrics_enabled:
        return
    
    try:
        # Check if JobMatcher instance has required methods
        if not hasattr(job_matcher, "get_top_jobs_by_multiple_metrics"):
            logger.warning("JobMatcher instance does not have get_top_jobs_by_multiple_metrics method")
            return
        
        if not hasattr(job_matcher, "process_job"):
            logger.warning("JobMatcher instance does not have process_job method")
            return
        
        # Instrument get_top_jobs_by_multiple_metrics method if not already instrumented
        original_get_top_jobs = job_matcher.get_top_jobs_by_multiple_metrics
        if not hasattr(original_get_top_jobs, "__wrapped__"):
            job_matcher.get_top_jobs_by_multiple_metrics = matching_algorithm_timer(
                "get_top_jobs_by_multiple_metrics"
            )(original_get_top_jobs)
        
        # Instrument process_job method if not already instrumented
        original_process_job = job_matcher.process_job
        if not hasattr(original_process_job, "__wrapped__"):
            job_matcher.process_job = async_matching_algorithm_timer(
                "process_job"
            )(original_process_job)
        
        logger.info("JobMatcher instance instrumented with metrics collection")
        
    except Exception as e:
        logger.error(
            "Failed to instrument JobMatcher instance",
            error=str(e)
        )