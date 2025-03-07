"""
Job matching asynchronous processing module.

This module provides functionality for processing job matching requests asynchronously,
allowing the API to return quickly while the matching happens in the background.
"""

import asyncio
import time
import uuid
from datetime import datetime, timedelta, UTC
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple

from app.core.config import settings
from app.log.logging import logger
from app.schemas.location import LocationFilter
from app.libs.job_matcher import JobMatcher
from app.metrics.tasks import async_task_timer


class TaskStatus(str, Enum):
    """Enumeration of possible task statuses."""
    PENDING = "pending"
    PROCESSING = "processing" 
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class TaskManager:
    """Manages asynchronous job matching tasks."""
    
    # In-memory task storage (will be replaced with Redis in a production implementation)
    # Structure: {task_id: (status, result, created_at, updated_at)}
    _tasks: Dict[str, Tuple[TaskStatus, Optional[Dict], datetime, datetime]] = {}
    
    # Task expiration time (default: 1 hour)
    _task_expiration = timedelta(hours=1)
    
    # Background task for cleanup
    _cleanup_task: Optional[asyncio.Task] = None
    
    # Class lock for task operations
    _lock = asyncio.Lock()
    
    @classmethod
    async def create_task(cls) -> str:
        """
        Create a new task and return its ID.
        
        Returns:
            str: The ID of the created task
        """
        task_id = str(uuid.uuid4())
        
        async with cls._lock:
            now = datetime.now(UTC)
            cls._tasks[task_id] = (TaskStatus.PENDING, None, now, now)
            
        logger.info(
            "Created new job matching task",
            task_id=task_id,
            status=TaskStatus.PENDING
        )
        
        return task_id
    
    @classmethod
    async def get_task_status(cls, task_id: str) -> Tuple[Optional[TaskStatus], Optional[Dict]]:
        """
        Get the status and result of a task.
        
        Args:
            task_id: The ID of the task
            
        Returns:
            Tuple containing task status and result (if available)
        """
        async with cls._lock:
            if task_id not in cls._tasks:
                return None, None
            
            status, result, _, _ = cls._tasks[task_id]
            return status, result
    
    @classmethod
    async def update_task_status(
        cls, 
        task_id: str, 
        status: TaskStatus, 
        result: Optional[Dict] = None
    ) -> bool:
        """
        Update the status and optionally the result of a task.
        
        Args:
            task_id: The ID of the task
            status: The new status
            result: Optional result data
            
        Returns:
            True if update was successful, False otherwise
        """
        async with cls._lock:
            if task_id not in cls._tasks:
                return False
            
            _, existing_result, created_at, _ = cls._tasks[task_id]
            
            # Merge with existing result if necessary
            final_result = result if result is not None else existing_result
            
            # Update task status and result
            cls._tasks[task_id] = (status, final_result, created_at, datetime.now(UTC))
            
            logger.info(
                "Updated job matching task status",
                task_id=task_id,
                status=status
            )
            
            return True
    
    @classmethod
    async def process_task(
        cls,
        task_id: str,
        resume: Dict[str, Any],
        location: Optional[LocationFilter] = None,
        keywords: Optional[List[str]] = None,
        offset: int = 0,
    ) -> None:
        """
        Process a job matching task asynchronously.
        
        Args:
            task_id: The ID of the task
            resume: Resume data containing vector embeddings
            location: Optional location filters
            keywords: Optional keyword filters
            offset: Optional results offset
        """
        try:
            # Update task status to processing
            await cls.update_task_status(task_id, TaskStatus.PROCESSING)
            
            # Create matcher instance
            matcher = JobMatcher()
            
            # Process job matching
            match_results = await matcher.process_job(
                resume,
                location=location,
                keywords=keywords,
                offset=offset
            )
            
            # Update task with results
            await cls.update_task_status(task_id, TaskStatus.COMPLETED, match_results)
            
            logger.info(
                "Job matching task completed successfully",
                task_id=task_id,
                matches_found=len(match_results.get("jobs", []))
            )
            
        except Exception as e:
            # Update task status to failed
            error_result = {
                "error": str(e),
                "error_type": type(e).__name__
            }
            
            await cls.update_task_status(task_id, TaskStatus.FAILED, error_result)
            
            logger.error(
                "Job matching task failed",
                task_id=task_id,
                error=str(e),
                error_type=type(e).__name__
            )
    
    @classmethod
    @async_task_timer("job_matching_task_processor")
    async def process_job_matching(
        cls,
        task_id: str,
        resume: Dict[str, Any],
        location: Optional[LocationFilter] = None,
        keywords: Optional[List[str]] = None,
        offset: int = 0,
    ) -> None:
        """
        Process a job matching task asynchronously with timing metrics.
        
        Args:
            task_id: The ID of the task
            resume: Resume data containing vector embeddings
            location: Optional location filters
            keywords: Optional keyword filters
            offset: Optional results offset
        """
        await cls.process_task(task_id, resume, location, keywords, offset)
    
    @classmethod
    async def cleanup_expired_tasks(cls) -> None:
        """Periodically clean up expired tasks."""
        try:
            logger.info("Starting task cleanup process")
            
            while True:
                try:
                    # Get current time
                    now = datetime.now(UTC)
                    expired_task_ids = []
                    
                    # Find expired tasks
                    async with cls._lock:
                        for task_id, (status, _, created_at, _) in cls._tasks.items():
                            # Check if task has expired
                            if now - created_at > cls._task_expiration:
                                expired_task_ids.append(task_id)
                    
                    # Mark tasks as expired
                    for task_id in expired_task_ids:
                        await cls.update_task_status(task_id, TaskStatus.EXPIRED)
                        
                        # In a production implementation with Redis, we would delete the task here
                        # For the in-memory implementation, we'll keep them for debugging
                    
                    if expired_task_ids:
                        logger.info(
                            "Cleaned up expired tasks",
                            expired_count=len(expired_task_ids)
                        )
                    
                    # Sleep for 5 minutes before next cleanup
                    await asyncio.sleep(300)
                    
                except asyncio.CancelledError:
                    # Exit loop if task is cancelled
                    break
                    
                except Exception as e:
                    logger.error(
                        "Error during task cleanup",
                        error=str(e),
                        error_type=type(e).__name__
                    )
                    # Sleep for 1 minute on error
                    await asyncio.sleep(60)
                
        except Exception as e:
            logger.error(
                "Fatal error in task cleanup process",
                error=str(e),
                error_type=type(e).__name__
            )
    
    @classmethod
    async def start_cleanup_task(cls) -> None:
        """Start the background task cleanup process."""
        if cls._cleanup_task is None or cls._cleanup_task.done():
            cls._cleanup_task = asyncio.create_task(cls.cleanup_expired_tasks())
            logger.info("Started task cleanup process")
    
    @classmethod
    async def stop_cleanup_task(cls) -> None:
        """Stop the background task cleanup process."""
        if cls._cleanup_task is not None and not cls._cleanup_task.done():
            cls._cleanup_task.cancel()
            try:
                await cls._cleanup_task
                logger.info("Stopped task cleanup process")
            except asyncio.CancelledError:
                pass
            cls._cleanup_task = None


# Initialize tasks on module import
async def setup_task_manager():
    """Set up the task manager during application startup."""
    await TaskManager.start_cleanup_task()


async def teardown_task_manager():
    """Tear down the task manager during application shutdown."""
    await TaskManager.stop_cleanup_task()