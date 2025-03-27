# Redis Cache Performance Considerations

This document provides guidance on optimizing the performance of the Redis caching implementation, including benchmarks, tuning parameters, and best practices.

## Performance Characteristics

### Baseline Performance

Under typical conditions with a properly configured Redis server, you can expect:

- **Get operations**: < 1ms average latency
- **Set operations**: < 2ms average latency
- **Serialization overhead**: 0.1-0.5ms for typical objects
- **Network latency**: 0.1-2ms depending on deployment topology

### Factors Affecting Performance

1. **Redis Server Configuration**
   - Memory allocation
   - Persistence settings
   - Eviction policies
   - Network configuration

2. **Client Configuration**
   - Connection pool settings
   - Serialization methods
   - Timeout values
   - Retry mechanisms

3. **Data Characteristics**
   - Size of cached objects
   - Complexity of objects (serialization cost)
   - Key design and length
   - TTL settings

4. **Deployment Topology**
   - Network distance between app and Redis
   - Redis replication configuration
   - Load balancing
   - Number of clients accessing Redis

## Performance Optimization Strategies

### 1. Data Size Optimization

Large objects can significantly impact Redis performance due to:
- Increased serialization/deserialization time
- Increased network transfer time
- Higher memory usage

**Recommendations:**

- **Consider size limits**: Objects over 1MB should be evaluated carefully
- **Compress large objects**: Use compression for text-heavy objects
- **Split large objects**: Break into smaller logical pieces when possible
- **Use selective caching**: Cache only the most important parts of large objects

**Implementation Example:**
```python
# For large objects, consider compression
from app.libs.redis.serialization import RedisSerializer

# Specialized serializer for large objects
large_object_serializer = RedisSerializer.serialize_with_compression(
    large_data,
    compress_threshold=1024  # Compress if over 1KB
)
```

### 2. Key Design Optimization

Well-designed cache keys are crucial for performance and maintainability.

**Recommendations:**

- **Use namespaces**: Structure keys with prefixes (e.g., `user:123:profile`)
- **Keep keys short but descriptive**: Shorter keys use less memory
- **Use consistent patterns**: Standardize key formats across the application
- **Consider key cardinality**: Too many unique keys can impact Redis performance

**Implementation Example:**
```python
# Instead of this
key = await cache.generate_key(
    user_id,
    product_id,
    timestamp=datetime.now().isoformat()  # BAD: High cardinality
)

# Do this
key = await cache.generate_key(
    f"user:{user_id}",
    f"product:{product_id}",
    view_type="detail"  # Better: Lower cardinality
)
```

### 3. TTL Strategy Optimization

Thoughtful TTL (Time-To-Live) strategies can significantly improve cache efficiency.

**Recommendations:**

- **Align TTL with data volatility**: Match TTL to how often data changes
- **Use staggered TTLs**: Add small random variations to prevent mass expirations
- **Consider hot vs. cold data**: Use shorter TTLs for frequently changing data
- **Implement proactive refresh**: Update cache before expiration for critical data

**Implementation Example:**
```python
import random

# Add jitter to prevent thundering herd problem
base_ttl = 300  # 5 minutes
jitter = random.uniform(0.8, 1.2)  # ±20% variation
effective_ttl = int(base_ttl * jitter)

# Create cache with jittered TTL
custom_cache = await RedisCacheFactory.create_cache(ttl=effective_ttl)
```

### 4. Connection Pool Optimization

Properly configured connection pools are essential for high-throughput scenarios.

**Recommendations:**

- **Size pool appropriately**: `connections = (cores * 2) + effective_concurrency`
- **Set reasonable timeouts**: Balance between responsiveness and resource usage
- **Monitor pool metrics**: Track usage patterns to optimize settings
- **Consider separate pools**: Use different pools for different types of operations

**Implementation Example:**
```python
# Optimized connection manager for high-throughput scenario
high_throughput_manager = RedisConnectionManager(
    host=settings.redis_host,
    port=settings.redis_port,
    max_connections=50,  # Higher for high-concurrency applications
    connection_timeout=1.0,  # Lower timeout for faster failure detection
    health_check_interval=10  # More frequent health checks
)

# Create specialized cache with this connection manager
specialized_cache = RedisCache(connection_manager=high_throughput_manager)
```

### 5. Serialization Optimization

Efficient serialization/deserialization is critical for Redis cache performance.

**Recommendations:**

- **Use the right serializer**: JSON for human-readable data, MessagePack or similar for better performance
- **Cache serialized forms**: For frequently accessed, rarely changed data
- **Profile serialization costs**: Identify expensive serialization operations
- **Consider schema validation**: Balance between validation safety and performance

**Current Implementation:**
The default implementation uses JSON serialization with optimizations for common types like datetime and UUID.

**Potential Enhancements:**
```python
# Import a faster JSON library if available
try:
    import orjson as json_lib
    def _serialize(obj):
        return json_lib.dumps(obj, default=default_serializer).decode('utf-8')
    def _deserialize(data_str):
        return json_lib.loads(data_str)
except ImportError:
    import json as json_lib
    def _serialize(obj):
        return json_lib.dumps(obj, default=default_serializer)
    def _deserialize(data_str):
        return json_lib.loads(data_str, object_hook=object_hook)
```

## Performance Benchmarking

### Benchmark Methodology

When evaluating Redis cache performance, consider testing:

1. **Throughput**: Operations per second the system can handle
2. **Latency**: Time to complete individual operations
3. **Scalability**: Performance under increasing load
4. **Resilience**: Behavior during Redis failure and recovery

### Sample Benchmark Code

```python
import asyncio
import time
from app.libs.redis.factory import RedisCacheFactory

async def benchmark_redis_cache(iterations=1000, payload_size_kb=10):
    """
    Benchmark Redis cache performance.
    
    Args:
        iterations: Number of operations to perform
        payload_size_kb: Size of test payload in KB
    """
    # Create test cache
    cache = await RedisCacheFactory.create_cache(
        ttl=60,
        namespace="benchmark"
    )
    
    # Create test payload
    payload = {
        "data": "x" * (payload_size_kb * 1024)
    }
    
    # Benchmark set operations
    start_time = time.time()
    for i in range(iterations):
        key = f"benchmark:set:{i}"
        await cache.set(key, payload)
    set_elapsed = time.time() - start_time
    set_ops_per_sec = iterations / set_elapsed
    
    # Benchmark get operations
    start_time = time.time()
    for i in range(iterations):
        key = f"benchmark:set:{i}"
        await cache.get(key)
    get_elapsed = time.time() - start_time
    get_ops_per_sec = iterations / get_elapsed
    
    # Benchmark mixed operations
    start_time = time.time()
    for i in range(iterations):
        key = f"benchmark:mixed:{i}"
        await cache.set(key, payload)
        await cache.get(key)
    mixed_elapsed = time.time() - start_time
    mixed_ops_per_sec = (iterations * 2) / mixed_elapsed
    
    # Report results
    print(f"=== Redis Cache Benchmark Results ===")
    print(f"Payload size: {payload_size_kb} KB")
    print(f"SET operations: {set_ops_per_sec:.2f} ops/sec ({set_elapsed*1000/iterations:.2f} ms/op)")
    print(f"GET operations: {get_ops_per_sec:.2f} ops/sec ({get_elapsed*1000/iterations:.2f} ms/op)")
    print(f"Mixed operations: {mixed_ops_per_sec:.2f} ops/sec ({mixed_elapsed*1000/(iterations*2):.2f} ms/op)")
```

### Expected Benchmark Results

On a typical deployment with Redis and the application in the same region:

| Operation | Payload Size | Operations/sec | Latency (ms) |
|-----------|--------------|----------------|--------------|
| GET       | 1 KB         | 5,000-10,000   | 0.1-0.2      |
| SET       | 1 KB         | 3,000-7,000    | 0.15-0.3     |
| GET       | 10 KB        | 2,000-5,000    | 0.2-0.5      |
| SET       | 10 KB        | 1,000-3,000    | 0.3-1.0      |
| GET       | 100 KB       | 200-1,000      | 1.0-5.0      |
| SET       | 100 KB       | 100-500        | 2.0-10.0     |

*Note: Actual performance will vary based on hardware, network, and Redis configuration.*

## Advanced Performance Optimizations

### Redis Server Optimizations

1. **Memory Configuration**:
   - Set `maxmemory` appropriate to your server
   - Choose appropriate `maxmemory-policy` (e.g., `volatile-lru` for TTL-based eviction)
   - Monitor `used_memory` and `used_memory_rss` for memory fragmentation

2. **Persistence Configuration**:
   - Use RDB snapshots instead of AOF for cache-only deployments
   - If using AOF, consider `appendfsync everysec` as a compromise
   - Schedule RDB snapshots during low-usage periods

3. **Network Tuning**:
   - Increase TCP backlog with `tcp-backlog`
   - Optimize kernel parameters:
     - `net.core.somaxconn`
     - `net.ipv4.tcp_max_syn_backlog`
     - `vm.overcommit_memory = 1`

4. **Client-Side Timeout Optimization**:
   - Align client timeout with server `timeout` setting
   - Set appropriate `tcp-keepalive` (default 300 seconds)

### Operational Best Practices

1. **Monitoring Performance**:
   - Track operation latency by key pattern and operation type
   - Monitor memory usage and fragmentation
   - Set alerts for sudden changes in hit rates or latency

2. **Avoiding Key Hotspots**:
   - Distribute keys evenly across keyspace
   - Split high-frequency keys across multiple keys if possible
   - Consider key sharding for extremely high volume keys

3. **Deployment Strategies**:
   - Co-locate Redis and application instances when possible
   - Use Redis Cluster for larger deployments
   - Consider read replicas for read-heavy workloads

## Common Performance Pitfalls

### 1. Large Objects in Redis

**Problem**: Storing multi-megabyte objects in Redis leads to high memory usage, network transfer costs, and increased serialization times.

**Solution**: 
- Split large objects into smaller logical pieces
- Store large data in specialized storage (S3, database) and cache metadata or references
- Use compression for large text-based data

### 2. Key Explosion

**Problem**: Unbounded growth in the number of unique keys, often due to user IDs, timestamps, or session IDs in keys.

**Solution**:
- Use expiration (TTL) on all keys
- Review key design to reduce cardinality
- Implement key cleanup mechanisms
- Monitor key growth rates

### 3. Inefficient Serialization

**Problem**: Slow serialization/deserialization becoming a bottleneck.

**Solution**:
- Profile serialization performance 
- Consider faster serialization libraries (e.g., ujson, orjson, msgpack)
- Optimize object structure for serialization
- Cache pre-serialized versions of static data

### 4. Connection Management Issues

**Problem**: Excessive connections or connection churn to Redis.

**Solution**:
- Use connection pooling
- Size connection pools appropriately
- Reuse connections when possible
- Monitor connection counts

### 5. Improper TTL Strategy

**Problem**: Cache misses due to premature expiration or memory pressure.

**Solution**:
- Balance TTL with data volatility
- Use staggered expirations
- Implement background refresh for critical data
- Monitor and tune TTL based on hit rates