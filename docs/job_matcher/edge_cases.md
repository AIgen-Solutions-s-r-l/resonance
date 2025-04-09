# Job Matcher Edge Cases and Error Handling

This document details the edge cases encountered in the job matching system and how they are handled to ensure robustness and reliability.

> **Note:** This document has been updated to include edge cases related to the new cooled jobs filtering feature. For more information on this feature, see [Cooled Jobs Filtering](./cooled_jobs_filtering.md).

## Resume Vector Validation

### Empty or Missing Vector

**Edge Case**: The resume doesn't contain a vector embedding or the vector is empty.

**Handling**:
```python
if "vector" not in resume:
    logger.warning("No vector found in resume")
    return {"jobs": []}
```

**Rationale**: Since vector similarity is the core matching mechanism, a missing vector makes meaningful matching impossible. The system returns an empty result set with appropriate logging rather than failing.

### Invalid Vector Format

**Edge Case**: The vector is present but in an invalid format (not a list, wrong dimensions, etc.).

**Handling**:
```python
vector_length = len(resume['vector']) if isinstance(resume.get('vector'), list) else 'unknown'
logger.info(f"RESUME CHECK: Vector found in resume, length: {vector_length}")

# Later validation during processing
if not isinstance(cv_embedding, list) or len(cv_embedding) != expected_dimension:
    logger.error("Invalid vector format or dimension")
    return {"jobs": []}
```

**Rationale**: Type and dimension checking prevents database errors when executing vector operations. The system logs detailed information for debugging.

## Database Query Handling

### Small Result Sets

**Edge Case**: Very few jobs match the filtering criteria (≤ 5 jobs).

**Handling**:
```python
if row_count <= 5:
    logger.info("Using fallback strategy due to small result set")
    result = await self.similarity_searcher._execute_fallback_query(...)
```

**Rationale**: For small result sets, the overhead of vector operations may not be justified. The system uses a simpler query to ensure some results are returned.

### Zero Results After Filtering

**Edge Case**: No jobs match the filtering criteria.

**Handling**:
```python
# In the fallback query implementation
if not results:
    logger.info("No results found after filtering")
    return []
```

**Rationale**: The system gracefully handles empty result sets by returning an empty list rather than failing.

### Database Connection Failures

**Edge Case**: Temporary database connection issues.

**Handling**:
```python
@retry_async(max_attempts=3, delay=0.5)
async def execute_query(...):
    # Query execution code
```

**Rationale**: The retry decorator attempts the operation multiple times with exponential backoff, handling transient connection issues.

## Data Validation

### Invalid Job Data

**Edge Case**: Job data from the database is incomplete or malformed.

**Handling**:
```python
def validate_row_data(self, row: dict) -> bool:
    return all(field in row for field in self.REQUIRED_FIELDS)

def create_job_match(self, row: dict) -> Optional[JobMatch]:
    if not self.validate_row_data(row):
        logger.warning("Skipping job match due to missing required fields")
        return None
    # ...
```

**Rationale**: The JobValidator component ensures that only valid job data is processed and returned, filtering out incomplete or malformed records.

### Type Conversion Errors

**Edge Case**: Data type conversion errors when processing database results.

**Handling**:
```python
try:
    job_match = JobMatch(
        id=str(row['id']),
        # ...
        score=float(row.get('score', 0.0)),
        # ...
    )
except Exception as e:
    logger.error(
        "Failed to create JobMatch instance",
        error=str(e),
        error_type=type(e).__name__,
        elapsed_time=f"{elapsed:.6f}s",
        row=row
    )
    return None
```

**Rationale**: Explicit type conversion with error handling prevents crashes due to unexpected data types.

## Cache Management

### Cache Size Limits

**Edge Case**: Cache grows too large, consuming excessive memory.

**Handling**:
```python
if len(self._cache) > self._max_size:
    logger.info(f"Cache cleanup triggered (size={len(self._cache)})")
    # Remove oldest entries
    sorted_items = sorted(self._cache.items(), key=lambda x: x[1][1])
    to_remove = len(self._cache) // 2  # Remove half of the entries
    
    for k, _ in sorted_items[:to_remove]:
        del self._cache[k]
```

**Rationale**: Size-based cleanup prevents memory issues by removing the oldest entries when the cache exceeds its maximum size.

### Cache Key Generation

**Edge Case**: Complex or nested objects in cache key parameters.

**Handling**:
```python
async def generate_key(self, *args, **kwargs) -> str:
    key_parts = []
    
    # Add positional args
    for arg in args:
        if arg is not None:
            key_parts.append(str(arg))
    
    # Add keyword args
    for k, v in sorted(kwargs.items()):
        if v is not None:
            if isinstance(v, list):
                v = sorted(v)
            key_parts.append(f"{k}_{v}")
    
    key = "_".join(str(part) for part in key_parts)
    return key
```

**Rationale**: The cache key generation handles various data types and structures, ensuring consistent keys for the same logical queries.

## Concurrency Handling

### Race Conditions in Cache

**Edge Case**: Multiple concurrent requests trying to access or modify the cache.

**Handling**:
```python
async def get(self, key: str) -> Optional[Dict[str, Any]]:
    async with self._lock:
        # Cache access code
        
async def set(self, key: str, results: Dict[str, Any]) -> None:
    async with self._lock:
        # Cache modification code
```

**Rationale**: Async locks prevent race conditions when multiple coroutines access or modify the cache simultaneously.

### Parallel Database Queries

**Edge Case**: Multiple concurrent database queries causing connection pool exhaustion.

**Handling**:
```python
async with get_db_cursor("default") as cursor:
    # Database operations
```

**Rationale**: The connection pool manager ensures efficient reuse of database connections and prevents pool exhaustion.

## Persistence Errors

### MongoDB Connection Failures

**Edge Case**: Failures when saving results to MongoDB.

**Handling**:
```python
try:
    # MongoDB operations
    await matches_collection.insert_one(job_results_with_meta)
except Exception as e:
    logger.error(
        "Failed to save matches to MongoDB",
        error=str(e),
        error_type=type(e).__name__,
        elapsed_time=f"{elapsed:.6f}s",
        resume_id=resume_id
    )
    # Continue execution without failing the entire operation
```

**Rationale**: Persistence errors are logged but don't cause the entire operation to fail, as persistence is often a non-critical operation.

### Applied and Cooled Jobs Retrieval Failures

**Edge Case**: Failures when retrieving applied or cooled job IDs from MongoDB.

**Handling**:
```python
# For applied jobs
try:
    applied_ids = await applied_jobs_service.get_applied_jobs(user_id)
except Exception as e:
    logger.error(f"Error fetching applied job IDs: {e}")
    applied_ids = None # Proceed without filtering on error

# For cooled jobs
try:
    cooled_ids = await cooled_jobs_service.get_cooled_jobs()
except Exception as e:
    logger.error(f"Error fetching cooled job IDs: {e}")
    cooled_ids = None # Proceed without filtering on error
```

**Rationale**: Failures in retrieving filtering data should not prevent the core job matching functionality from working. The system gracefully degrades by proceeding without filtering when necessary.

### File System Errors

**Edge Case**: Failures when saving results to the file system.

**Handling**:
```python
try:
    with open(filename, "w") as f:
        json.dump(job_results, f, indent=2)
except Exception as e:
    logger.error(
        "Failed to save matches to file",
        error=str(e),
        error_type=type(e).__name__,
        filename=filename
    )
    # Continue execution without failing the entire operation
```

**Rationale**: File system errors are logged but don't cause the entire operation to fail.

## Performance Edge Cases

### Slow Queries

**Edge Case**: Queries taking longer than expected.

**Handling**:
```python
start_time = time()
# Operation code
elapsed = time() - start_time
if elapsed > 1.0:
    logger.warning(f"Slow operation detected: {func_name}", elapsed_time=f"{elapsed:.6f}s")
```

**Rationale**: Performance logging helps identify and address slow operations.

### Large Result Sets

**Edge Case**: Very large result sets consuming excessive memory.

**Handling**:
```python
# Limit is enforced in the query
LIMIT %s
```

**Rationale**: Result limiting prevents memory issues when dealing with large result sets.

## Error Recovery Strategies

### Graceful Degradation

The system implements graceful degradation strategies:

1. **Vector to Non-Vector Fallback**: Falls back to simpler queries when vector operations are not feasible
2. **Caching for Resilience**: Serves cached results when database operations fail
3. **Partial Results**: Returns partial results when some but not all operations succeed
4. **Default Values**: Uses sensible defaults when specific data is missing
5. **Filtering Bypass**: Continues without filtering when applied or cooled job IDs cannot be retrieved

### Comprehensive Logging

All edge cases and errors are logged with detailed context:

```python
logger.error(
    "Error message",
    error=str(e),
    error_type=type(e).__name__,
    elapsed_time=f"{elapsed:.6f}s",
    context_variable=context_value
)
```

This detailed logging enables:
1. Effective debugging
2. Performance monitoring
3. Error pattern identification
4. System health assessment