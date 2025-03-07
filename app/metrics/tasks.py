"""
Background tasks for metrics collection.

This module provides functionality for running periodic background tasks
to collect metrics at regular intervals.
"""

import asyncio
import functools
import threading
import time
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set, Tuple, TypeVar, cast

from app.core.config import settings
from app.log.logging import logger
from app.metrics.core import increment_counter, report_timing
from app.metrics.system import collect_system_metrics


# Function type variable
F = TypeVar('F', bound=Callable[..., Any])

# Type for collection tasks
TaskFunc = Callable[[], Any]
# Updated for modern Python compatibility (asyncio.coroutine is deprecated)
AsyncTaskFunc = Callable[[], Awaitable[Any]]

# Collection thread state
_collection_thread: Optional[threading.Thread] = None
_collection_tasks: Dict[str, Tuple[TaskFunc, int]] = {}
_collection_thread_running = False
_collection_thread_lock = threading.Lock()

# Async collection tasks
_async_collection_tasks: Dict[str, Tuple[AsyncTaskFunc, int]] = {}
_async_task: Optional[asyncio.Task] = None


def task_timer(
    task_name: str,
    tags: Optional[Dict[str, str]] = None
) -> Callable[[F], F]:
    """
    Decorator to time task execution.
    
    Args:
        task_name: Name of the task
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
                "task": task_name
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
                
                # Update tags for success
                metric_tags["status"] = "success"
                
                # Report timing
                report_timing("task.duration", duration_ms, metric_tags)
                
                # Increment counter
                increment_counter("task.count", metric_tags)
                
                return result
                
            except Exception as e:
                # Calculate duration
                duration = time.time() - start_time
                duration_ms = duration * 1000.0
                
                # Update tags for error
                metric_tags["status"] = "error"
                metric_tags["error_type"] = e.__class__.__name__
                
                # Report timing with error tags
                report_timing("task.duration", duration_ms, metric_tags)
                
                # Increment error counter
                increment_counter("task.count", metric_tags)
                
                # Re-raise the exception
                raise
                
        return cast(F, wrapper)
    return decorator


def async_task_timer(
    task_name: str,
    tags: Optional[Dict[str, str]] = None
) -> Callable[[F], F]:
    """
    Decorator to time async task execution.
    
    Args:
        task_name: Name of the task
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
                "task": task_name
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
                
                # Update tags for success
                metric_tags["status"] = "success"
                
                # Report timing
                report_timing("task.duration", duration_ms, metric_tags)
                
                # Increment counter
                increment_counter("task.count", metric_tags)
                
                return result
                
            except Exception as e:
                # Calculate duration
                duration = time.time() - start_time
                duration_ms = duration * 1000.0
                
                # Update tags for error
                metric_tags["status"] = "error"
                metric_tags["error_type"] = e.__class__.__name__
                
                # Report timing with error tags
                report_timing("task.duration", duration_ms, metric_tags)
                
                # Increment error counter
                increment_counter("task.count", metric_tags)
                
                # Re-raise the exception
                raise
                
        return cast(F, wrapper)
    return decorator


def register_collection_task(
    name: str,
    task_func: TaskFunc,
    interval_seconds: int = 60
) -> bool:
    """
    Register a task for periodic collection.
    
    Args:
        name: Task name
        task_func: Task function
        interval_seconds: Collection interval in seconds
        
    Returns:
        True if registration was successful, False otherwise
    """
    if not settings.metrics_enabled or not settings.metrics_collection_enabled:
        return False
    
    try:
        with _collection_thread_lock:
            _collection_tasks[name] = (task_func, interval_seconds)
            
        logger.debug(
            "Registered collection task",
            task=name,
            interval=interval_seconds
        )
        
        return True
        
    except Exception as e:
        logger.error(
            "Failed to register collection task",
            task=name,
            error=str(e)
        )
        return False


def unregister_collection_task(name: str) -> bool:
    """
    Unregister a task from periodic collection.
    
    Args:
        name: Task name
        
    Returns:
        True if unregistration was successful, False otherwise
    """
    try:
        with _collection_thread_lock:
            if name in _collection_tasks:
                del _collection_tasks[name]
                
                logger.debug(
                    "Unregistered collection task",
                    task=name
                )
                
                return True
            else:
                logger.debug(
                    "Collection task not found",
                    task=name
                )
                
                return False
        
    except Exception as e:
        logger.error(
            "Failed to unregister collection task",
            task=name,
            error=str(e)
        )
        return False


def get_task_status() -> Dict[str, Dict[str, Any]]:
    """
    Get the status of registered collection tasks.
    
    Returns:
        Dictionary of task status information
    """
    status = {}
    
    try:
        with _collection_thread_lock:
            for name, (_, interval) in _collection_tasks.items():
                status[name] = {
                    "type": "sync",
                    "interval": interval,
                    "running": _collection_thread_running
                }
                
            for name, (_, interval) in _async_collection_tasks.items():
                status[name] = {
                    "type": "async",
                    "interval": interval,
                    "running": _async_task is not None and not _async_task.done()
                }
                
        return status
        
    except Exception as e:
        logger.error(
            "Failed to get task status",
            error=str(e)
        )
        return {"error": str(e)}


def _collection_thread_func() -> None:
    """Background thread function for running collection tasks."""
    global _collection_thread_running
    
    logger.info("Metrics collection thread started")
    
    # Track last run time for each task
    last_run_times: Dict[str, float] = {}
    
    try:
        _collection_thread_running = True
        
        while _collection_thread_running:
            try:
                current_time = time.time()
                
                # Copy tasks to prevent issues with concurrent modification
                with _collection_thread_lock:
                    tasks = list(_collection_tasks.items())
                
                # Run due tasks
                for name, (task_func, interval) in tasks:
                    # Skip if task has been removed
                    if name not in _collection_tasks:
                        continue
                        
                    # Check if task is due
                    last_run = last_run_times.get(name, 0)
                    if current_time - last_run >= interval:
                        try:
                            # Run task
                            task_func()
                            
                            # Update last run time
                            last_run_times[name] = current_time
                            
                        except Exception as e:
                            logger.error(
                                "Error running collection task",
                                task=name,
                                error=str(e)
                            )
                
                # Sleep a short interval (1 second) to check for new tasks
                time.sleep(1)
                
            except Exception as e:
                logger.error(
                    "Error in collection thread",
                    error=str(e)
                )
                time.sleep(5)  # Sleep longer on error
            
    except Exception as e:
        logger.error(
            "Fatal error in collection thread",
            error=str(e)
        )
    
    finally:
        _collection_thread_running = False
        logger.info("Metrics collection thread stopped")


async def _async_collection_func() -> None:
    """Async function for running collection tasks."""
    logger.info("Async metrics collection started")
    
    # Track last run time for each task
    last_run_times: Dict[str, float] = {}
    
    try:
        while True:
            try:
                current_time = time.time()
                
                # Copy tasks to prevent issues with concurrent modification
                tasks = list(_async_collection_tasks.items())
                
                # Run due tasks
                for name, (task_func, interval) in tasks:
                    # Skip if task has been removed
                    if name not in _async_collection_tasks:
                        continue
                        
                    # Check if task is due
                    last_run = last_run_times.get(name, 0)
                    if current_time - last_run >= interval:
                        try:
                            # Run task
                            await task_func()
                            
                            # Update last run time
                            last_run_times[name] = current_time
                            
                        except Exception as e:
                            logger.error(
                                "Error running async collection task",
                                task=name,
                                error=str(e)
                            )
                
                # Sleep a short interval (1 second) to check for new tasks
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                logger.info("Async metrics collection task cancelled")
                break
                
            except Exception as e:
                logger.error(
                    "Error in async collection task",
                    error=str(e)
                )
                await asyncio.sleep(5)  # Sleep longer on error
            
    except Exception as e:
        logger.error(
            "Fatal error in async collection task",
            error=str(e)
        )
    
    finally:
        logger.info("Async metrics collection stopped")


def start_metrics_collection() -> bool:
    """
    Start the metrics collection thread and register default tasks.
    
    Returns:
        True if collection was started successfully, False otherwise
    """
    global _collection_thread
    
    if not settings.metrics_enabled or not settings.metrics_collection_enabled:
        return False
    
    with _collection_thread_lock:
        # Skip if already running
        if _collection_thread is not None and _collection_thread.is_alive():
            logger.debug("Metrics collection thread already running")
            return True
        
        try:
            # Register system metrics collection
            if settings.system_metrics_enabled:
                register_collection_task(
                    "system_metrics",
                    collect_system_metrics,
                    settings.system_metrics_interval
                )
            
            # Start collection thread
            _collection_thread = threading.Thread(
                target=_collection_thread_func,
                daemon=True
            )
            _collection_thread.start()
            
            logger.info(
                "Started metrics collection thread",
                tasks=list(_collection_tasks.keys())
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to start metrics collection thread",
                error=str(e)
            )
            return False


def stop_metrics_collection() -> bool:
    """
    Stop the metrics collection thread.
    
    Returns:
        True if collection was stopped successfully, False otherwise
    """
    global _collection_thread, _collection_thread_running
    
    with _collection_thread_lock:
        # Skip if not running
        if _collection_thread is None or not _collection_thread.is_alive():
            logger.debug("Metrics collection thread not running")
            return True
        
        try:
            # Signal thread to stop
            _collection_thread_running = False
            
            # Wait for thread to stop (with timeout)
            _collection_thread.join(timeout=5.0)
            
            # Check if thread stopped
            if _collection_thread.is_alive():
                logger.warning("Metrics collection thread did not stop gracefully")
            else:
                logger.info("Stopped metrics collection thread")
                _collection_thread = None
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to stop metrics collection thread",
                error=str(e)
            )
            return False


def register_async_collection_task(
    name: str,
    task_func: AsyncTaskFunc,
    interval_seconds: int = 60
) -> bool:
    """
    Register an async task for periodic collection.
    
    Args:
        name: Task name
        task_func: Async task function
        interval_seconds: Collection interval in seconds
        
    Returns:
        True if registration was successful, False otherwise
    """
    if not settings.metrics_enabled or not settings.metrics_collection_enabled:
        return False
    
    try:
        _async_collection_tasks[name] = (task_func, interval_seconds)
        
        logger.debug(
            "Registered async collection task",
            task=name,
            interval=interval_seconds
        )
        
        return True
        
    except Exception as e:
        logger.error(
            "Failed to register async collection task",
            task=name,
            error=str(e)
        )
        return False


def unregister_async_collection_task(name: str) -> bool:
    """
    Unregister an async task from periodic collection.
    
    Args:
        name: Task name
        
    Returns:
        True if unregistration was successful, False otherwise
    """
    try:
        if name in _async_collection_tasks:
            del _async_collection_tasks[name]
            
            logger.debug(
                "Unregistered async collection task",
                task=name
            )
            
            return True
        else:
            logger.debug(
                "Async collection task not found",
                task=name
            )
            
            return False
        
    except Exception as e:
        logger.error(
            "Failed to unregister async collection task",
            task=name,
            error=str(e)
        )
        return False


async def start_async_metrics_collection() -> bool:
    """
    Start async metrics collection tasks.
    
    Returns:
        True if async collection was started successfully, False otherwise
    """
    global _async_task
    
    if not settings.metrics_enabled or not settings.metrics_collection_enabled:
        return False
    
    # Skip if already running
    if _async_task is not None and not _async_task.done():
        logger.debug("Async metrics collection already running")
        return True
    
    try:
        # Start async collection task
        _async_task = asyncio.create_task(_async_collection_func())
        
        logger.info(
            "Started async metrics collection",
            tasks=list(_async_collection_tasks.keys())
        )
        
        return True
        
    except Exception as e:
        logger.error(
            "Failed to start async metrics collection",
            error=str(e)
        )
        return False


async def stop_async_metrics_collection() -> bool:
    """
    Stop async metrics collection tasks.
    
    Returns:
        True if async collection was stopped successfully, False otherwise
    """
    global _async_task
    
    # Skip if not running
    if _async_task is None or _async_task.done():
        logger.debug("Async metrics collection not running")
        return True
    
    try:
        # Cancel async task
        _async_task.cancel()
        
        # Wait for task to cancel
        try:
            await asyncio.wait_for(_async_task, timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("Async metrics collection did not stop gracefully")
        except asyncio.CancelledError:
            logger.info("Async metrics collection stopped")
        
        _async_task = None
        
        return True
        
    except Exception as e:
        logger.error(
            "Failed to stop async metrics collection",
            error=str(e)
        )
        return False