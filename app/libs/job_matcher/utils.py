"""
Utility functions for job matcher.

This module contains helper utilities used by the job matcher.
"""

from typing import List, Any, Callable, Awaitable
from time import time
from loguru import logger
from functools import wraps
import inspect


def log_performance(func_name: str, elapsed: float, **kwargs) -> None:
    """
    Log performance metrics.
    
    Args:
        func_name: Function name
        elapsed: Elapsed time in seconds
        **kwargs: Additional context
    """
    log_data = {
        "function": func_name,
        "elapsed_time": f"{elapsed:.6f}s",
        **kwargs
    }
    
    # Log as different levels based on elapsed time
    if elapsed > 1.0:
        logger.warning(f"Slow operation detected: {func_name}", **log_data)
    elif elapsed > 0.5:
        logger.info(f"Operation timing: {func_name}", **log_data)
    else:
        logger.debug(f"Operation completed: {func_name}", **log_data)


def performance_log(func):
    """
    Decorator to log function performance.
    
    Args:
        func: Function to be decorated
        
    Returns:
        Decorated function with performance logging
    """
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time()
        try:
            result = await func(*args, **kwargs)
            elapsed = time() - start_time
            log_performance(func.__name__, elapsed)
            return result
        except Exception as e:
            elapsed = time() - start_time
            logger.error(
                f"Error in {func.__name__}",
                error=str(e),
                error_type=type(e).__name__,
                elapsed_time=f"{elapsed:.6f}s"
            )
            raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time()
        try:
            result = func(*args, **kwargs)
            elapsed = time() - start_time
            log_performance(func.__name__, elapsed)
            return result
        except Exception as e:
            elapsed = time() - start_time
            logger.error(
                f"Error in {func.__name__}",
                error=str(e),
                error_type=type(e).__name__,
                elapsed_time=f"{elapsed:.6f}s"
            )
            raise
    
    if inspect.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def trace_sql_execution(query: str, params: List[Any]) -> None:
    """
    Log SQL query execution for debugging.
    
    Args:
        query: SQL query
        params: Query parameters
    """
    # Truncate query and params for logging
    max_query_length = 1000
    truncated_query = query[:max_query_length] + "..." if len(query) > max_query_length else query
    
    # Sanitize params for logging
    sanitized_params = []
    for param in params:
        if isinstance(param, str) and len(param) > 100:
            sanitized_params.append(param[:50] + "...")
        else:
            sanitized_params.append(param)
    
    logger.debug(
        "Executing SQL query",
        query=truncated_query,
        params=sanitized_params
    )


def retry_async(max_attempts: int = 3, delay: float = 0.5):
    """
    Retry decorator for async functions.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Delay between retries in seconds
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable[..., Awaitable]):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            import asyncio
            
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts:
                        wait_time = delay * attempt
                        logger.warning(
                            f"Attempt {attempt} failed, retrying in {wait_time:.2f}s",
                            function=func.__name__,
                            error=str(e),
                            error_type=type(e).__name__
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed",
                            function=func.__name__,
                            error=str(e),
                            error_type=type(e).__name__
                        )
            
            # If we reached here, all attempts failed
            assert last_exception is not None
            raise last_exception
            
        return wrapper
    return decorator