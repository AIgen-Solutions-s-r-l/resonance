# Vector Operation Bugs Analysis

## Bugs Identified

Our testing revealed two significant issues:

### 1. Synchronous Legacy Endpoint Failure
```
===== Testing Synchronous Legacy Endpoint =====
{"detail":"An unexpected error occurred."}
```
This indicates an unhandled exception in the legacy endpoint.

### 2. Vector Operation Type Error
```
Poll attempt 1...
Status response: {"task_id":"87b29d18-995c-43d5-976b-e5ecb47ad01b","status":"failed","result":{"error":"operator does not exist: integer - vector\nLINE 28: (1 - embedding <=> $4::vector) * 0.4\n ^\nHINT: No operator matches the given name and argument types. You might need to add explicit type casts.","error_type":"UndefinedFunction"},"created_at":"2025-03-07T23:41:03.517739+00:00","updated_at":"2025-03-07T23:41:03.517739+00:00"}
Current status: failed
```

## Root Causes

### Vector Operation Error

The error occurs in this expression:
```sql
(1 - embedding <=> $4::vector) * 0.4
```

This operation tries to:
1. Calculate the cosine distance between vectors (`embedding <=> $4::vector`)
2. Subtract this value from 1 (`1 - embedding <=> $4::vector`)
3. Multiply by 0.4 to weight the result

The issue is that PostgreSQL doesn't know how to handle subtraction between an integer (`1`) and a vector result. The `<=>` operator returns a value, but direct arithmetic with this value needs proper type casting.

## Recommended Fix

Update the vector similarity calculation in `app/utils/db_utils.py` to add proper type casting:

```python
# Current problematic code:
query = f"""
SELECT
    ...
    (
        -- L2 distance (weighted 0.4)
        (1 - (embedding <-> %s::vector) / 
            CASE WHEN (SELECT MAX(embedding <-> %s::vector) FROM "Jobs" j2 {where_sql}) = 0 
            THEN 1 ELSE (SELECT MAX(embedding <-> %s::vector) FROM "Jobs" j2 {where_sql}) END
        ) * 0.4
        +
        -- Cosine distance (weighted 0.4)
        (1 - embedding <=> %s::vector) * 0.4
        +
        -- Inner product (weighted 0.2)
        ((embedding <#> %s::vector) * -1 + 1) * 0.2
    ) AS score
FROM "Jobs" j
...
"""

# Fixed code with explicit type casting:
query = f"""
SELECT
    ...
    (
        -- L2 distance (weighted 0.4)
        (1.0 - (embedding <-> %s::vector)::float / 
            CASE WHEN (SELECT MAX(embedding <-> %s::vector) FROM "Jobs" j2 {where_sql}) = 0 
            THEN 1.0 ELSE (SELECT MAX(embedding <-> %s::vector)::float FROM "Jobs" j2 {where_sql}) END
        ) * 0.4
        +
        -- Cosine distance (weighted 0.4)
        (1.0 - (embedding <=> %s::vector)::float) * 0.4
        +
        -- Inner product (weighted 0.2)
        ((embedding <#> %s::vector)::float * -1.0 + 1.0) * 0.2
    ) AS score
FROM "Jobs" j
...
"""
```

Key changes:
1. Use explicit `::float` type casting for vector operation results
2. Use `1.0` instead of `1` for floating-point constants
3. Apply consistent type handling throughout the calculation

## Implementation Note

These bugs demonstrate that while the asynchronous architecture is working correctly (immediate response, task creation), there are still issues with the actual vector operation implementation. This is common when implementing complex mathematical operations in SQL, especially with specialized extensions like pgvector.

The good news is that the architectural improvements are successful - the API returns immediately, and errors are properly tracked and reported through the task status system rather than causing API timeouts.