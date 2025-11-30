# Bug Report — MongoDB Connection Not Awaited at Module Level

## Summary
- Scope/Area: core/mongodb
- Type: functional — Severity: S1
- Environment: Python 3.10-3.12, Motor 3.6.0, Branch: main, Commit: 0368b8aa40f03ca5048ba51bd9a441bde183b7c3

## Expected vs Actual
- Expected: MongoDB connection initialization should be properly awaited in async context
- Actual: Connection ping command `client.admin.command("ping")` is called at module import time without await, mixing sync/async operations

## Steps to Reproduce
1. Examine `app/core/mongodb.py:14-21`
2. Import the module in an async context
3. Observe the synchronous `client.admin.command("ping")` call at module level
4. Note potential warnings or errors in async runtime
5. Connection validation happens synchronously, potentially blocking event loop

## Evidence
**Code snippet from app/core/mongodb.py:14-21:**
```python
client = AsyncIOMotorClient(settings.mongodb, serverSelectionTimeoutMS=5000)
database = client[settings.mongodb_database]
collection_name = database.get_collection("resumes")
user_collection = database.get_collection("user_operations")
client.admin.command("ping")  # NOT AWAITED - this is synchronous!
```

**Recent changes**: N/A

## Root Cause Analysis
**5 Whys:**
1. Why is ping not awaited? → Developer mixed async client with sync ping call
2. Why wasn't this caught? → No async/await validation in linting or testing
3. Why does it seem to work? → Motor tolerates some sync operations, but this is incorrect
4. Why initialize at module level? → Convenience, but violates async best practices
5. Why ping at import? → Attempting early connection validation, but done incorrectly

**Causal chain:** Module import → Async client created → Sync ping called without await → Potential event loop blocking → May cause warnings or race conditions during startup

## Remediation
**Workaround/Mitigation:**
Currently works by chance, but this is fragile and may fail in stricter async environments.

**Proposed permanent fix:**
Move connection initialization to an async startup function called during FastAPI lifespan:

```python
# app/core/mongodb.py
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional

_client: Optional[AsyncIOMotorClient] = None
_database = None
_collection_name = None
_user_collection = None

async def connect_mongodb():
    """Initialize MongoDB connection - call during application startup"""
    global _client, _database, _collection_name, _user_collection

    _client = AsyncIOMotorClient(settings.mongodb, serverSelectionTimeoutMS=5000)
    _database = _client[settings.mongodb_database]
    _collection_name = _database.get_collection("resumes")
    _user_collection = _database.get_collection("user_operations")

    # Properly await the ping
    await _client.admin.command("ping")
    logger.info("MongoDB connection established successfully")

async def close_mongodb():
    """Close MongoDB connection - call during application shutdown"""
    global _client
    if _client:
        _client.close()
        logger.info("MongoDB connection closed")

# Expose getters
def get_database():
    return _database

def get_collection_name():
    return _collection_name

def get_user_collection():
    return _user_collection

# app/main.py - in lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_mongodb()  # Properly initialize
    yield
    await close_mongodb()  # Properly cleanup
```

**Risk & rollback considerations:**
- Medium risk: Changes initialization pattern
- Need to update all imports to use getter functions or update lifespan
- Rollback: Keep old module-level init as backup

## Validation & Prevention
**Test plan:**
1. Implement async connection initialization
2. Add test for proper async/await usage
3. Verify no event loop warnings during startup
4. Load test to ensure connection pool works correctly
5. Test graceful shutdown

**Regression tests:**
```python
@pytest.mark.asyncio
async def test_mongodb_connection_is_async():
    """Verify MongoDB connection is properly async"""
    from app.core.mongodb import connect_mongodb
    import asyncio

    # Should be awaitable
    assert asyncio.iscoroutinefunction(connect_mongodb)

    # Should complete without blocking
    await connect_mongodb()

    # Connection should be established
    from app.core.mongodb import get_database
    db = get_database()
    assert db is not None

    # Should be able to perform async operations
    result = await db.command("ping")
    assert result.get("ok") == 1
```

**Monitoring/alerts:**
- Add async/await linting rules (ruff can detect this)
- Monitor for event loop blocking warnings in production

## Ownership & Next Steps
- Owner(s): Backend team / Database infrastructure owner
- Dependencies/links:
  - File: `app/core/mongodb.py:14-21`
  - File: `app/main.py` (lifespan function needs update)
  - Related: All files that import from `app.core.mongodb`

**Checklist:**
- [x] Reproducible steps verified
- [x] Evidence attached/linked
- [x] RCA written and reviewed
- [ ] Fix implemented/validated
- [ ] Regression tests merged
