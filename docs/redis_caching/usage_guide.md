# Redis Cache Usage Guide

This guide provides examples and best practices for using the Redis caching implementation in the job matching service.

## Basic Usage

The Redis cache is designed to be a drop-in replacement for the previous in-memory cache, maintaining the same interface. In most cases, you can continue using the cache as before:

```python
from app.libs.job_matcher.cache import cache

# Generate a cache key
key = await cache.generate_key(user_id, location=location_filter, keywords=keywords)

# Get cached data
cached_results = await cache.get(key)
if cached_results:
    return cached_results
    
# Process data and store in cache
results = await process_data()
await cache.set(key, results)
```

## Cache Initialization

The cache is automatically initialized during application startup. If you need to initialize it manually (e.g., in tests), you can use:

```python
from app.libs.job_matcher.cache import initialize_cache

# Initialize the cache
await initialize_cache()
```

## Creating Custom Cache Instances

For specialized caching needs, you can create custom cache instances:

```python
from app.libs.redis.factory import RedisCacheFactory

# Create a custom cache with specific settings
custom_cache = await RedisCacheFactory.create_cache(
    ttl=600,  # 10 minutes TTL
    namespace="custom_feature",
    max_retries=3
)

# Use the custom cache
await custom_cache.set("my_key", {"data": "value"})
data = await custom_cache.get("my_key")
```

## Key Generation

Proper key generation is crucial for efficient caching. Use the `generate_key` method to create consistent keys:

```python
# Basic key generation
key1 = await cache.generate_key("user_123", "query_param")

# With keyword arguments
key2 = await cache.generate_key(
    user_id,
    offset=offset,
    location=location_filter.dict() if location_filter else None,
    keywords=keywords
)

# With complex objects
key3 = await cache.generate_key(
    resume_id,
    filters=json.dumps(filters_dict)  # Serialize complex objects for key generation
)
```

### Key Generation Best Practices

1. **Use stable identifiers** - IDs, slugs, or other stable values that don't change frequently
2. **Sort lists** in key components to ensure consistent ordering
3. **Serialize complex objects** consistently (e.g., use JSON)
4. **Include version information** if data format might change
5. **Keep keys readable** for debugging purposes
6. **Consider key length** - very long keys can impact performance

## Error Handling

The Redis cache implementation includes robust error handling, but you might want to add additional handling in critical sections:

```python
try:
    result = await cache.get(key)
    if result:
        return result
except Exception as e:
    logger.warning(f"Cache retrieval failed: {str(e)}")
    # Continue without cached data
```

## Monitoring Cache Performance

The Redis cache implementation includes metrics integration. You can monitor cache performance through the metrics system:

```python
# In your metrics dashboard, look for these metrics:
# - redis.cache.hit - Cache hit count
# - redis.cache.miss - Cache miss count
# - redis.cache.get_latency - Time taken for get operations
# - redis.cache.set_latency - Time taken for set operations
# - redis.cache.error - Error count
# - redis.circuit_breaker.* - Circuit breaker state metrics
```

## Clearing Cache Data

In some cases, you might need to clear cached data:

```python
from app.libs.redis.factory import RedisCacheFactory

# Create a namespaced cache
namespaced_cache = await RedisCacheFactory.create_cache(namespace="feature_x")

# Clear all data in this namespace
await namespaced_cache.clear_namespace()
```

## Example: Caching Job Match Results

Here's a complete example showing how to cache job match results:

```python
async def get_job_matches(
    resume_id: str,
    location: Optional[LocationFilter] = None,
    keywords: Optional[List[str]] = None,
    offset: int = 0,
    use_cache: bool = True
) -> Dict[str, Any]:
    """Get job matches with caching."""
    
    # Early return if caching is disabled
    if not use_cache:
        return await perform_job_matching(resume_id, location, keywords, offset)
    
    # Generate cache key
    cache_key = await cache.generate_key(
        resume_id,
        offset=offset,
        location=location.dict() if location else None,
        keywords=keywords
    )
    
    # Try to get from cache
    cached_results = await cache.get(cache_key)
    if cached_results:
        logger.info(f"Using cached job matches for resume {resume_id}")
        return cached_results
    
    # Perform actual job matching
    logger.info(f"Cache miss, performing job matching for resume {resume_id}")
    results = await perform_job_matching(resume_id, location, keywords, offset)
    
    # Store in cache
    await cache.set(cache_key, results)
    
    return results
```

## Example: Using Cache in FastAPI Endpoint

Here's how to use the cache in a FastAPI endpoint:

```python
@router.get("/recommendations/{user_id}")
async def get_recommendations(
    user_id: int,
    skip_cache: bool = Query(False, description="Skip cache and force fresh results")
):
    # Generate cache key
    cache_key = await cache.generate_key(f"recommendations:{user_id}")
    
    # Try cache first if not skipped
    if not skip_cache:
        cached_results = await cache.get(cache_key)
        if cached_results:
            return cached_results
    
    # Get fresh results
    results = await generate_recommendations(user_id)
    
    # Cache the results
    await cache.set(cache_key, results)
    
    return results
```

## Advanced: Cache Invalidation Strategies

### Time-Based Invalidation

The simplest approach is to rely on TTL for cache invalidation:

```python
# Short TTL for frequently changing data
volatile_cache = await RedisCacheFactory.create_cache(ttl=60)  # 1 minute

# Long TTL for stable data
stable_cache = await RedisCacheFactory.create_cache(ttl=3600)  # 1 hour
```

### Manual Invalidation

For scenarios requiring explicit invalidation:

```python
# Delete a specific key
specific_key = await cache.generate_key(user_id, "profile")
await cache.delete(specific_key)

# Clear an entire namespace
user_cache = await RedisCacheFactory.create_cache(namespace=f"user:{user_id}")
await user_cache.clear_namespace()
```

### Event-Based Invalidation

For more complex scenarios, consider event-based invalidation:

```python
# When user data changes
async def update_user_profile(user_id: int, data: Dict[str, Any]):
    # Update database
    await db.update_user(user_id, data)
    
    # Invalidate cache
    profile_key = await cache.generate_key(user_id, "profile")
    await cache.delete(profile_key)
    
    # Optionally invalidate related caches
    recommendations_key = await cache.generate_key(f"recommendations:{user_id}")
    await cache.delete(recommendations_key)
```

## Performance Considerations

1. **Cache appropriate data** - Cache expensive operations, not trivial ones
2. **Set appropriate TTL** - Balance freshness vs. performance
3. **Monitor hit rate** - Low hit rates may indicate ineffective caching
4. **Be mindful of data size** - Very large objects can slow down serialization
5. **Use namespaces** - Organize cache data logically
6. **Consider warm-up strategies** - Pre-populate cache for common queries

## Troubleshooting

### Common Issues

1. **Cache misses when hits expected**
   - Check TTL settings
   - Verify key generation is consistent
   - Check if clear_namespace was called

2. **Slow cache performance**
   - Check Redis server load
   - Review network latency
   - Examine object size and serialization overhead

3. **Connection errors**
   - Verify Redis server is running
   - Check network connectivity
   - Review Redis logs for errors

4. **High memory usage**
   - Review TTL settings
   - Check cached object sizes
   - Consider Redis eviction policies

### Debugging Tips

```python
# Enable debug logging
import logging
logging.getLogger("app.libs.redis").setLevel(logging.DEBUG)

# Check cache operation
key = await cache.generate_key("test")
await cache.set(key, {"test": "data"})
result = await cache.get(key)
print(f"Cache test: {result}")

# Check Redis connection directly
from app.libs.redis.factory import RedisCacheFactory
redis = await RedisCacheFactory._connection_manager.get_redis()
await redis.ping()  # Should return True