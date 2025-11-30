# Bug Report — Applied Jobs Service Silent Failure Hides Errors

## Summary
- Scope/Area: services/applied_jobs
- Type: functional — Severity: S2 (High)
- Environment: Python 3.10-3.12, MongoDB, Branch: main, Commit: 0368b8aa40f03ca5048ba51bd9a441bde183b7c3

## Expected vs Actual
- Expected: Database errors should propagate to caller so they can be handled appropriately
- Actual: Service returns empty list on any exception, silently swallowing errors including database connection failures

## Steps to Reproduce
1. Simulate MongoDB connection failure (stop MongoDB or corrupt connection string)
2. Make authenticated request to `GET /jobs/match`
3. AppliedJobsService.get_applied_jobs() catches exception and returns `[]`
4. Matcher proceeds assuming user has no applied jobs
5. User may see jobs they've already applied to (data inconsistency)
6. No error visible to user or in API response

## Evidence
**Code from app/services/applied_jobs_service.py:45-52:**
```python
except Exception as e:
    logger.exception(
        "Error fetching applied jobs for user %s: %s",
        user_id,
        str(e)
    )
    return []  # SILENTLY FAILS - caller doesn't know if it's empty or error
```

**Impact scenario:**
```python
# In matching_service.py
applied_jobs = await AppliedJobsService.get_applied_jobs(user_id, portal)

# Returns [] on both:
# 1. User has no applied jobs (legitimate)
# 2. Database error occurred (error!)

# Caller cannot distinguish, proceeds with empty filter
# User sees duplicate jobs they already applied for
```

**Recent changes**: N/A

## Root Cause Analysis
**5 Whys:**
1. Why return empty list on error? → Developer assumed "fail open" is better than failing request
2. Why not propagate exception? → Wanted to avoid breaking entire matching flow
3. Why not return error indication? → No Result/Either type pattern in codebase
4. Why is this problematic? → Caller cannot distinguish between legitimate empty and error
5. Why matters for users? → Users see already-applied jobs, poor UX and data inconsistency

**Causal chain:** Database error occurs → Exception caught → Empty list returned → Caller assumes no applied jobs → Matching proceeds without filter → User sees duplicate jobs → Confusion and poor UX

## Remediation
**Workaround/Mitigation:**
Monitor logs for "Error fetching applied jobs" and alert immediately. Current behavior at least logs errors even if swallowed.

**Proposed permanent fix:**
OPTION 1 - Propagate exceptions (recommended for critical path):
```python
async def get_applied_jobs(cls, user_id: int, portal: str = "all") -> List[int]:
    """
    Get list of job IDs that user has applied for.
    Raises exception if database error occurs.
    """
    try:
        collection = database.get_collection("user_operations")
        query = {"user_id": user_id}

        if portal != "all":
            query["portal"] = portal

        documents = await collection.find(query).to_list(length=None)

        applied_jobs = [
            doc["job_id"]
            for doc in documents
            if "job_id" in doc
        ]

        logger.info(f"Found {len(applied_jobs)} applied jobs for user {user_id}")
        return applied_jobs

    except Exception as e:
        logger.exception(f"Error fetching applied jobs for user {user_id}: {str(e)}")
        # PROPAGATE - let caller handle error appropriately
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve applied jobs. Please try again."
        )
```

OPTION 2 - Return Result type (better long-term):
```python
from typing import Union, List
from dataclasses import dataclass

@dataclass
class Success:
    value: List[int]

@dataclass
class Error:
    message: str

Result = Union[Success, Error]

async def get_applied_jobs(cls, user_id: int, portal: str = "all") -> Result:
    try:
        # ... fetch logic ...
        return Success(value=applied_jobs)
    except Exception as e:
        logger.exception(f"Error fetching applied jobs: {str(e)}")
        return Error(message=str(e))

# In caller:
result = await AppliedJobsService.get_applied_jobs(user_id)
if isinstance(result, Success):
    applied_jobs = result.value
else:
    # Handle error appropriately
    raise HTTPException(status_code=500, detail=result.message)
```

OPTION 3 - Fail fast with cache fallback:
```python
async def get_applied_jobs(cls, user_id: int, portal: str = "all") -> List[int]:
    """
    Get applied jobs with cache fallback.
    Raises exception if both DB and cache fail.
    """
    cache_key = f"applied_jobs:{user_id}:{portal}"

    try:
        # Try database first
        collection = database.get_collection("user_operations")
        # ... fetch logic ...

        # Cache the result
        await redis.setex(cache_key, 300, json.dumps(applied_jobs))
        return applied_jobs

    except Exception as e:
        logger.exception(f"Database error, trying cache: {str(e)}")

        # Try cache as fallback
        cached = await redis.get(cache_key)
        if cached:
            logger.warning(f"Using cached applied jobs for user {user_id}")
            return json.loads(cached)

        # Both failed - propagate error
        logger.error(f"Both database and cache failed for user {user_id}")
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve applied jobs. Service temporarily unavailable."
        )
```

**Risk & rollback considerations:**
- Medium risk: Changes error handling behavior
- Users will see errors instead of wrong data (better UX)
- Need to ensure proper error messages
- Rollback: Return empty list if needed, but fix root cause first

## Validation & Prevention
**Test plan:**
1. Implement error propagation
2. Test with simulated MongoDB failures
3. Verify appropriate HTTP error codes returned
4. Test that errors are properly logged
5. Verify user sees helpful error message
6. Test cache fallback if implemented

**Regression tests:**
```python
@pytest.mark.asyncio
async def test_applied_jobs_propagates_database_errors(monkeypatch):
    """Verify get_applied_jobs propagates database errors instead of returning []"""
    from app.services.applied_jobs_service import AppliedJobsService
    from motor.motor_asyncio import AsyncIOMotorCollection

    # Mock database to raise exception
    async def mock_find(*args, **kwargs):
        raise Exception("Database connection failed")

    monkeypatch.setattr(AsyncIOMotorCollection, "find", mock_find)

    # Should raise exception, not return []
    with pytest.raises(Exception) as exc_info:
        await AppliedJobsService.get_applied_jobs(user_id=1)

    assert "Database connection failed" in str(exc_info.value)

@pytest.mark.asyncio
async def test_applied_jobs_empty_vs_error_distinguishable():
    """Verify caller can distinguish between no jobs and error"""
    from app.services.applied_jobs_service import AppliedJobsService

    # Test 1: User with no applied jobs
    result = await AppliedJobsService.get_applied_jobs(user_id=999999)
    assert result == [] or isinstance(result, Success) with result.value == []

    # Test 2: Database error
    with patch('app.core.mongodb.database') as mock_db:
        mock_db.get_collection.side_effect = Exception("Connection failed")

        # Should raise or return Error, NOT empty list
        with pytest.raises(Exception):
            await AppliedJobsService.get_applied_jobs(user_id=1)

@pytest.mark.asyncio
async def test_matching_handles_applied_jobs_error():
    """Verify matching service handles applied jobs errors gracefully"""
    from app.services.matching_service import MatchingService

    # Simulate applied jobs service failure
    with patch('app.services.applied_jobs_service.AppliedJobsService.get_applied_jobs') as mock:
        mock.side_effect = Exception("Database unavailable")

        # Matching should return appropriate error to user
        with pytest.raises(HTTPException) as exc_info:
            await MatchingService.get_matched_jobs(user_id=1)

        assert exc_info.value.status_code in [500, 503]
        assert "applied jobs" in exc_info.value.detail.lower() or "unavailable" in exc_info.value.detail.lower()
```

**Monitoring/alerts:**
- Alert on "Error fetching applied jobs" log entries
- Monitor applied jobs cache hit/miss ratio
- Track 500/503 errors from matching endpoint
- Alert if error rate > 1%

## Ownership & Next Steps
- Owner(s): Backend team / Services layer owner
- Dependencies/links:
  - File: `app/services/applied_jobs_service.py:45-52` (error handling)
  - File: `app/services/cooled_jobs_service.py` (same pattern - needs fixing too!)
  - File: `app/services/matching_service.py` (caller needs to handle errors)

**Checklist:**
- [x] Reproducible steps verified
- [x] Evidence attached/linked
- [x] RCA written and reviewed
- [ ] Fix implemented/validated
- [ ] Error handling pattern standardized across services
- [ ] Regression tests added
- [ ] Monitoring alerts configured
