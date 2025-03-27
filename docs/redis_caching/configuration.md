# Redis Cache Configuration Guide

This guide covers the configuration options for the Redis caching implementation in the job matching service.

## Environment Variables

Redis connection settings are configured through environment variables:

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `REDIS_HOST` | Redis server hostname | `localhost` | `redis.example.com` |
| `REDIS_PORT` | Redis server port | `6379` | `6380` |
| `REDIS_DB` | Redis database number | `0` | `1` |
| `REDIS_PASSWORD` | Redis password (if required) | `""` (empty) | `secretpassword` |

## Additional Configuration Parameters

The Redis cache implementation has several parameters that can be adjusted programmatically:

### Cache TTL

The Time-To-Live (TTL) for cache entries determines how long entries remain valid before expiring:

```python
# Default TTL is 300 seconds (5 minutes)
cache = await RedisCacheFactory.create_cache(ttl=300)

# For longer-lived data (1 hour)
cache = await RedisCacheFactory.create_cache(ttl=3600)

# For short-lived data (30 seconds)
cache = await RedisCacheFactory.create_cache(ttl=30)
```

### Cache Namespace

Namespaces allow you to segment the cache for different purposes or services:

```python
# Default namespace is "matching"
cache = await RedisCacheFactory.create_cache(namespace="matching")

# For a specific feature
cache = await RedisCacheFactory.create_cache(namespace="job_recommendations")

# For test environments
cache = await RedisCacheFactory.create_cache(namespace="test_matching")
```

### Retry Configuration

The retry mechanism is configurable for handling transient Redis errors:

```python
# Default max retries is 3
cache = await RedisCacheFactory.create_cache(max_retries=3)

# For more aggressive retrying
cache = await RedisCacheFactory.create_cache(max_retries=5)

# To disable retrying
cache = await RedisCacheFactory.create_cache(max_retries=0)
```

## Circuit Breaker Configuration

The circuit breaker behavior can be configured when creating a connection manager:

```python
# Create a custom circuit breaker
circuit_breaker = CircuitBreaker(
    failure_threshold=5,  # Open after 5 failures
    reset_timeout=30      # Try again after 30 seconds
)

# Create connection manager with custom circuit breaker
connection_manager = RedisConnectionManager(
    host=settings.redis_host,
    port=settings.redis_port,
    circuit_breaker=circuit_breaker
)
```

## Connection Pool Settings

The Redis connection pool settings control how connections are managed:

```python
# Create connection manager with custom pool settings
connection_manager = RedisConnectionManager(
    host=settings.redis_host,
    port=settings.redis_port,
    max_connections=10,        # Maximum connections in pool
    connection_timeout=2.0,    # Connect/operation timeout in seconds
    health_check_interval=30   # Health check interval in seconds
)
```

## Example Configuration File

For containerized deployments, you can use a `.env` file with the following settings:

```dotenv
# Redis configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=my_secure_password

# Application settings
SERVICE_NAME=matching_service
ENVIRONMENT=production
```

## Development vs. Production Settings

### Development

For development environments, the default configuration uses:
- Local Redis instance (`localhost:6379`)
- No password
- Debug logging
- Short health check intervals

### Production

For production, we recommend:
- Redis with authentication
- Redis in the same region as the application
- Firewall rules to restrict access
- Appropriate connection pool size based on instance count
- Monitoring and alerting on Redis metrics

## Multiple Caches with Different Settings

You can create multiple cache instances with different settings for various use cases:

```python
# Short-lived cache for frequently changing data
frequent_cache = await RedisCacheFactory.create_cache(
    ttl=60,
    namespace="frequent_updates",
    max_retries=2
)

# Long-lived cache for static data
static_cache = await RedisCacheFactory.create_cache(
    ttl=86400,  # 24 hours
    namespace="static_data",
    max_retries=5
)
```

## Configuration Best Practices

1. **Use environment variables** for Redis connection settings
2. **Set appropriate TTL** based on data volatility
3. **Use namespaces** to separate different types of cached data
4. **Adjust connection pool size** based on instance count
5. **Configure circuit breaker** based on acceptable failure rates
6. **Monitor Redis metrics** to identify performance issues
7. **Use authentication** in production environments
8. **Keep Redis and application** in the same region/zone for low latency