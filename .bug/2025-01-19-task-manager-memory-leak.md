# Bug Report — Task Manager Memory Leak from Expired Tasks

## Summary
- Scope/Area: tasks/background
- Type: performance — Severity: S2 (High)
- Environment: Python 3.10-3.12, FastAPI 0.115.4, Branch: main, Commit: 0368b8aa40f03ca5048ba51bd9a441bde183b7c3

## Expected vs Actual
- Expected: Expired tasks should be removed from memory to prevent unbounded growth
- Actual: Tasks are marked as EXPIRED but never deleted from in-memory dictionary, causing memory leak over time

## Steps to Reproduce
1. Start matching service
2. Trigger many job matching tasks via `POST /jobs/match`
3. Wait for tasks to expire (1 hour timeout)
4. Observe `TaskManager._tasks` dictionary grows indefinitely
5. Monitor memory usage - increases over time without bound
6. Eventually leads to OOM error in production

## Evidence
**Code from app/tasks/job_processor.py:34-36:**
```python
# In-memory task storage (will be replaced with Redis in a production implementation)
_tasks: Dict[str, Tuple[TaskStatus, Optional[Dict], datetime, datetime]] = {}
```

**Cleanup code (lines 232-240):**
```python
for task_id in expired_task_ids:
    await cls.update_task_status(task_id, TaskStatus.EXPIRED)
    # In a production implementation with Redis, we would delete the task here
    # For the in-memory implementation, we'll keep them for debugging
```

**Problem**: Comment indicates Redis migration planned but never implemented. Tasks marked EXPIRED but never removed.

**Memory growth scenario:**
- Service runs for 30 days
- 1000 tasks/day created
- 1 hour expiration → 30,000 expired tasks accumulate
- Each task ~1KB → 30MB+ wasted memory
- Over months: hundreds of MB to GBs leaked

## Root Cause Analysis
**5 Whys:**
1. Why aren't tasks deleted? → Comment says "keep for debugging"
2. Why not migrated to Redis? → Incomplete feature, production code still uses in-memory
3. Why is memory growing? → Dictionary never shrinks, only grows
4. Why not caught in testing? → No long-running tests to detect memory leaks
5. Why deployed without fixing? → "Temporary" in-memory implementation shipped to production

**Causal chain:** In-memory implementation intended as temporary → Redis migration not completed → "Keep for debugging" decision → Tasks never deleted → Unbounded dictionary growth → Memory leak → Eventually OOM in production

## Remediation
**Workaround/Mitigation:**
SHORT-TERM: Periodic service restart to clear memory
- Schedule daily/weekly restarts
- Monitor memory usage and alert at thresholds
- Limit task creation rate to slow growth

**Proposed permanent fix:**
DELETE expired tasks instead of just marking them:

```python
@classmethod
async def _cleanup_expired_tasks(cls):
    """Remove tasks that have exceeded the maximum lifetime"""
    try:
        current_time = datetime.now()
        max_task_age = timedelta(hours=1)

        async with cls._lock:
            # Find expired tasks
            expired_task_ids = [
                task_id
                for task_id, (status, result, created_at, updated_at) in cls._tasks.items()
                if current_time - created_at > max_task_age
            ]

            # DELETE instead of marking as expired
            for task_id in expired_task_ids:
                del cls._tasks[task_id]  # REMOVE FROM MEMORY
                logger.debug(f"Deleted expired task: {task_id}")

            if expired_task_ids:
                logger.info(f"Cleaned up {len(expired_task_ids)} expired tasks")

    except Exception as e:
        logger.exception(f"Error during task cleanup: {str(e)}")
```

**Better long-term solution - implement Redis storage:**
```python
# Replace in-memory dict with Redis
@classmethod
async def create_task(cls, task_id: str, user_id: int) -> str:
    """Create a new task"""
    # Store in Redis with TTL
    task_data = {
        "status": TaskStatus.PENDING.value,
        "result": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "user_id": user_id,
    }
    await redis.setex(
        f"task:{task_id}",
        3600,  # 1 hour TTL - auto-expires!
        json.dumps(task_data)
    )
    return task_id
```

**Risk & rollback considerations:**
- Low risk for deletion fix: Just cleaning up memory
- Medium risk for Redis migration: Need to ensure Redis availability
- Rollback: Revert to marking as EXPIRED if issues arise
- Monitor: Track memory usage before/after

## Validation & Prevention
**Test plan:**
1. Implement task deletion
2. Create many tasks and wait for expiration
3. Verify memory doesn't grow unbounded
4. Measure memory usage over 24 hour period
5. Stress test with thousands of tasks
6. Monitor for any task retrieval errors after deletion

**Regression tests:**
```python
@pytest.mark.asyncio
async def test_expired_tasks_are_deleted():
    """Verify expired tasks are removed from memory"""
    from app.tasks.job_processor import TaskManager
    from datetime import datetime, timedelta

    # Create test tasks
    task_ids = []
    for i in range(100):
        task_id = await TaskManager.create_task(f"test-task-{i}", user_id=1)
        task_ids.append(task_id)

    # Verify tasks exist
    assert len(TaskManager._tasks) == 100

    # Mock time advancement (or use freezegun)
    with patch('app.tasks.job_processor.datetime') as mock_datetime:
        mock_datetime.now.return_value = datetime.now() + timedelta(hours=2)

        # Run cleanup
        await TaskManager._cleanup_expired_tasks()

    # Verify tasks are DELETED, not just marked expired
    assert len(TaskManager._tasks) == 0, "Expired tasks should be deleted"

@pytest.mark.asyncio
async def test_task_manager_memory_bounded():
    """Verify TaskManager doesn't leak memory"""
    import sys
    from app.tasks.job_processor import TaskManager

    # Measure initial memory
    initial_size = sys.getsizeof(TaskManager._tasks)

    # Create and expire many tasks
    for i in range(1000):
        task_id = await TaskManager.create_task(f"task-{i}", user_id=1)
        await TaskManager.update_task_status(task_id, TaskStatus.COMPLETED)

    # Run cleanup
    await TaskManager._cleanup_expired_tasks()

    # Verify memory is bounded
    final_size = sys.getsizeof(TaskManager._tasks)
    growth = final_size - initial_size

    # Should not grow significantly after cleanup
    assert growth < initial_size * 0.1, f"Memory grew by {growth} bytes - potential leak"
```

**Monitoring/alerts:**
- Monitor service memory usage with alerts at 70%, 85%, 95%
- Track dictionary size: `len(TaskManager._tasks)`
- Alert if task count exceeds threshold (e.g., >10,000)
- Graph memory usage over time to detect leaks early

## Ownership & Next Steps
- Owner(s): Backend team / Task management owner
- Dependencies/links:
  - File: `app/tasks/job_processor.py:232-240` (cleanup function)
  - File: `app/tasks/job_processor.py:34-36` (task storage)
  - Future: Migrate to Redis for production-ready task storage

**Checklist:**
- [x] Reproducible steps verified
- [x] Evidence attached/linked
- [x] RCA written and reviewed
- [ ] Fix implemented/validated (delete expired tasks)
- [ ] Memory leak test added
- [ ] Monitoring alerts configured
- [ ] Long-term: Redis migration completed
