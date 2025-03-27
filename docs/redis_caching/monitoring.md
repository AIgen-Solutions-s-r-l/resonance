# Redis Cache Monitoring Guide

This document provides guidance on monitoring the Redis caching implementation, including available metrics, recommended dashboards, and alerting strategies.

## Available Metrics

The Redis cache implementation exposes the following metrics for monitoring:

### Cache Performance Metrics

| Metric Name | Type | Description |
|-------------|------|-------------|
| `redis.cache.hit` | Counter | Number of cache hits |
| `redis.cache.miss` | Counter | Number of cache misses |
| `redis.cache.get_latency` | Timing | Time taken to retrieve data from Redis (ms) |
| `redis.cache.set_latency` | Timing | Time taken to store data in Redis (ms) |

### Error Metrics

| Metric Name | Type | Description |
|-------------|------|-------------|
| `redis.cache.error` | Counter | Total number of Redis errors |
| `redis.cache.connection_error` | Counter | Number of Redis connection errors |
| `redis.cache.serialization_error` | Counter | Number of serialization/deserialization errors |
| `redis.cache.retry` | Counter | Number of automatic retry attempts |

### Circuit Breaker Metrics

| Metric Name | Type | Description |
|-------------|------|-------------|
| `redis.circuit_breaker.open` | Counter | Number of times circuit breaker opened |
| `redis.circuit_breaker.close` | Counter | Number of times circuit breaker closed |
| `redis.circuit_breaker.half_open` | Counter | Number of times circuit breaker entered half-open state |
| `redis.circuit_breaker.skip` | Counter | Number of operations skipped due to open circuit |

### Redis Server Metrics

These metrics require additional monitoring of the Redis server itself:

| Metric Name | Type | Description |
|-------------|------|-------------|
| `redis.memory.used` | Gauge | Memory used by Redis |
| `redis.memory.max` | Gauge | Maximum memory available to Redis |
| `redis.clients.connected` | Gauge | Number of connected clients |
| `redis.commands.processed` | Counter | Number of commands processed |
| `redis.keyspace.hits` | Counter | Number of successful lookups in main dictionary |
| `redis.keyspace.misses` | Counter | Number of failed lookups in main dictionary |

## Metric Collection

The metrics system in the application is already set up to collect Redis metrics. The `RedisMetrics` class in `app/libs/redis/monitoring.py` provides the integration.

```python
# Example of how metrics are tracked
RedisMetrics.increment(RedisMetrics.HIT, 1)
RedisMetrics.timing(RedisMetrics.GET_LATENCY, elapsed_ms)
```

For Redis server metrics, you'll need to set up a separate collector like Redis Exporter for Prometheus or a similar tool for your metrics backend.

## Recommended Dashboards

### Cache Performance Dashboard

This dashboard focuses on cache effectiveness and performance:

**Panels:**
1. **Cache Hit Rate**: `sum(rate(redis.cache.hit[5m])) / (sum(rate(redis.cache.hit[5m])) + sum(rate(redis.cache.miss[5m])))`
2. **Cache Operation Latency**: 
   - Get Latency: `histogram_quantile(0.95, redis.cache.get_latency)`
   - Set Latency: `histogram_quantile(0.95, redis.cache.set_latency)`
3. **Cache Operations Per Second**:
   - Gets: `rate(redis.cache.hit[1m]) + rate(redis.cache.miss[1m])`
   - Sets: `rate(redis.cache.set_latency_count[1m])`
4. **Redis Memory Usage**: `redis.memory.used / redis.memory.max`

### Error Monitoring Dashboard

This dashboard focuses on error rates and circuit breaker status:

**Panels:**
1. **Redis Error Rate**: `rate(redis.cache.error[5m])`
2. **Error Types Breakdown**:
   - Connection Errors: `rate(redis.cache.connection_error[5m])`
   - Serialization Errors: `rate(redis.cache.serialization_error[5m])`
3. **Circuit Breaker Status**:
   - Open Events: `rate(redis.circuit_breaker.open[5m])`
   - Close Events: `rate(redis.circuit_breaker.close[5m])`
   - Half-Open Events: `rate(redis.circuit_breaker.half_open[5m])`
4. **Retry Rate**: `rate(redis.cache.retry[5m])`
5. **Operation Skip Rate**: `rate(redis.circuit_breaker.skip[5m])`

### Redis Server Dashboard

This dashboard focuses on Redis server health:

**Panels:**
1. **Connected Clients**: `redis.clients.connected`
2. **Commands Per Second**: `rate(redis.commands.processed[1m])`
3. **Memory Usage**: `redis.memory.used`
4. **Memory Fragmentation Ratio**: `redis.memory.fragmentation_ratio`
5. **Keyspace Hit Rate**: `redis.keyspace.hits / (redis.keyspace.hits + redis.keyspace.misses)`

## Alerting Recommendations

### Critical Alerts

These alerts require immediate attention:

1. **High Circuit Breaker Open Rate**
   - Condition: `rate(redis.circuit_breaker.open[5m]) > 0.2`
   - Description: Circuit breaker is opening frequently, indicating Redis connection issues
   - Response: Check Redis server status and network connectivity

2. **Low Cache Hit Rate**
   - Condition: `sum(rate(redis.cache.hit[15m])) / (sum(rate(redis.cache.hit[15m])) + sum(rate(redis.cache.miss[15m]))) < 0.5`
   - Description: Cache hit rate is below 50%, indicating potential cache issues
   - Response: Investigate cache invalidation, TTL settings, or Redis issues

3. **High Redis Error Rate**
   - Condition: `rate(redis.cache.error[5m]) / rate(redis.cache.get_latency_count[5m]) > 0.1`
   - Description: More than 10% of Redis operations are resulting in errors
   - Response: Check Redis server logs, network issues, or application bugs

### Warning Alerts

These alerts indicate potential issues that should be addressed soon:

1. **Increasing Cache Latency**
   - Condition: `histogram_quantile(0.95, redis.cache.get_latency) > 50`
   - Description: 95th percentile of cache get operations exceeding 50ms
   - Response: Check Redis load, network latency, or serialization overhead

2. **High Redis Memory Usage**
   - Condition: `redis.memory.used / redis.memory.max > 0.8`
   - Description: Redis memory usage above 80% of the limit
   - Response: Consider scaling Redis, reviewing cached data, or adjusting maxmemory policy

3. **Elevated Retry Rate**
   - Condition: `rate(redis.cache.retry[5m]) > 1`
   - Description: Operations are being retried frequently
   - Response: Investigate transient Redis errors or network issues

### Informational Alerts

These alerts provide useful information but don't necessarily require action:

1. **Circuit Breaker State Change**
   - Condition: `changes(redis.circuit_breaker.open[15m]) > 0 or changes(redis.circuit_breaker.close[15m]) > 0`
   - Description: Circuit breaker has changed state
   - Response: Monitor for continued issues

2. **Cache Hit Rate Change**
   - Condition: `abs(sum(rate(redis.cache.hit[1h])) / (sum(rate(redis.cache.hit[1h])) + sum(rate(redis.cache.miss[1h]))) - sum(rate(redis.cache.hit[1h] offset 1h)) / (sum(rate(redis.cache.hit[1h] offset 1h)) + sum(rate(redis.cache.miss[1h] offset 1h)))) > 0.2`
   - Description: Cache hit rate has changed by more than 20 percentage points in the last hour
   - Response: Investigate if expected or indicative of a problem

## Dashboard Implementation

### Prometheus + Grafana Example

If you're using Prometheus and Grafana, here's a sample dashboard configuration:

```json
{
  "annotations": {
    "list": [
      {
        "builtIn": 1,
        "datasource": "-- Grafana --",
        "enable": true,
        "hide": true,
        "iconColor": "rgba(0, 211, 255, 1)",
        "name": "Annotations & Alerts",
        "type": "dashboard"
      }
    ]
  },
  "editable": true,
  "gnetId": null,
  "graphTooltip": 0,
  "id": 123,
  "links": [],
  "panels": [
    {
      "aliasColors": {},
      "bars": false,
      "dashLength": 10,
      "dashes": false,
      "datasource": null,
      "fieldConfig": {
        "defaults": {
          "custom": {}
        },
        "overrides": []
      },
      "fill": 1,
      "fillGradient": 0,
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 0,
        "y": 0
      },
      "hiddenSeries": false,
      "id": 2,
      "legend": {
        "avg": false,
        "current": false,
        "max": false,
        "min": false,
        "show": true,
        "total": false,
        "values": false
      },
      "lines": true,
      "linewidth": 1,
      "nullPointMode": "null",
      "options": {
        "alertThreshold": true
      },
      "percentage": false,
      "pluginVersion": "7.3.7",
      "pointradius": 2,
      "points": false,
      "renderer": "flot",
      "seriesOverrides": [],
      "spaceLength": 10,
      "stack": false,
      "steppedLine": false,
      "targets": [
        {
          "expr": "sum(rate(redis_cache_hit_total[5m])) / (sum(rate(redis_cache_hit_total[5m])) + sum(rate(redis_cache_miss_total[5m])))",
          "interval": "",
          "legendFormat": "Hit Rate",
          "refId": "A"
        }
      ],
      "thresholds": [],
      "timeFrom": null,
      "timeRegions": [],
      "timeShift": null,
      "title": "Cache Hit Rate",
      "tooltip": {
        "shared": true,
        "sort": 0,
        "value_type": "individual"
      },
      "type": "graph",
      "xaxis": {
        "buckets": null,
        "mode": "time",
        "name": null,
        "show": true,
        "values": []
      },
      "yaxes": [
        {
          "format": "percentunit",
          "label": null,
          "logBase": 1,
          "max": "1",
          "min": "0",
          "show": true
        },
        {
          "format": "short",
          "label": null,
          "logBase": 1,
          "max": null,
          "min": null,
          "show": true
        }
      ],
      "yaxis": {
        "align": false,
        "alignLevel": null
      }
    }
  ],
  "schemaVersion": 26,
  "style": "dark",
  "tags": [],
  "templating": {
    "list": []
  },
  "time": {
    "from": "now-6h",
    "to": "now"
  },
  "timepicker": {},
  "timezone": "",
  "title": "Redis Cache Monitoring",
  "uid": "redis-cache-monitoring",
  "version": 1
}
```

## Monitoring Best Practices

1. **Establish Baselines**: Monitor normal operation to establish performance baselines
2. **Track Trends**: Look for trends rather than just absolute values
3. **Correlate Metrics**: Correlate Redis metrics with application metrics
4. **Adjust Thresholds**: Fine-tune alert thresholds based on application requirements
5. **Monitor Both Sides**: Monitor both the application's view of Redis and the Redis server itself
6. **Set Up Load Testing**: Use load testing to understand how metrics change under load
7. **Create Runbooks**: Develop runbooks for common issues identified by monitoring
8. **Regular Reviews**: Regularly review dashboards and alerts for relevance

## Troubleshooting with Metrics

| Symptom | Key Metrics to Check | Potential Causes |
|---------|----------------------|------------------|
| High latency | `redis.cache.get_latency`, `redis.memory.used` | Redis server overloaded, network issues, large objects |
| Low hit rate | `redis.cache.hit`, `redis.cache.miss` | Inappropriate TTL, cache invalidation issues, key generation problems |
| Frequent errors | `redis.cache.error`, `redis.circuit_breaker.open` | Redis connection issues, network problems, serialization errors |
| Memory issues | `redis.memory.used`, `redis.memory.fragmentation_ratio` | Memory leaks, large cached items, inappropriate maxmemory policy |