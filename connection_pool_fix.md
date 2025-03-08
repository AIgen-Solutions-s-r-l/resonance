# Connection Pool Initialization Fix

## Current Issue

The current implementation creates an AsyncConnectionPool with an approach that triggers a deprecation warning:

```python
# Current implementation
pool = AsyncConnectionPool(
    conninfo=settings.database_url,
    min_size=settings.db_pool_min_size,
    max_size=settings.db_pool_max_size,
    timeout=settings.db_pool_timeout,
    max_idle=settings.db_pool_max_idle,
    kwargs={"row_factory": dict_row}
)
await pool.wait()
```

Warning message:
```
RuntimeWarning: opening the async pool AsyncConnectionPool in the constructor is deprecated and will not be supported anymore in a future release. Please use `await pool.open()`, or use the pool as context manager using: `async with AsyncConnectionPool(...) as pool: `...
```

## Recommended Fix - Option 1: Disable auto-opening and use explicit open

```python
# Recommended implementation
pool = AsyncConnectionPool(
    conninfo=settings.database_url,
    min_size=settings.db_pool_min_size,
    max_size=settings.db_pool_max_size,
    timeout=settings.db_pool_timeout,
    max_idle=settings.db_pool_max_idle,
    kwargs={"row_factory": dict_row},
    open=False  # Don't open in constructor
)
await pool.open()  # Explicitly open the pool
```

## Recommended Fix - Option 2: Use as context manager

This approach works well for localized pool usage:

```python
async with AsyncConnectionPool(
    conninfo=settings.database_url,
    min_size=settings.db_pool_min_size,
    max_size=settings.db_pool_max_size,
    timeout=settings.db_pool_timeout,
    max_idle=settings.db_pool_max_idle,
    kwargs={"row_factory": dict_row}
) as pool:
    # Use the pool here
```

## Implementation Recommendation

For a global connection pool that's created at application startup, Option 1 is more appropriate as it allows the pool to persist beyond a specific context. The function `get_connection_pool` should be updated to use this approach.

This would eliminate the deprecation warning while maintaining the same functionality.