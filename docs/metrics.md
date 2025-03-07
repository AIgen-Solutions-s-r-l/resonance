# Matching Service Metrics Guide

This document provides a comprehensive overview of the metrics collected by the matching service and how to interpret them for monitoring performance, diagnosing issues, and improving service quality.

## Metrics Overview

The matching service collects metrics across several key areas:

1. **API Performance**
2. **Database Operations**
3. **Algorithm Performance**
4. **System Resources**
5. **Background Tasks**

All metrics are tagged with relevant information to enable detailed analysis.

## Metrics Collection Architecture

The service uses a pluggable metrics backend architecture that supports:

- **StatsD**: Basic metrics collection
- **DogStatsD**: Enhanced metrics collection with Datadog, including tags

Metrics can be enabled/disabled and sampled using configuration settings.

## Key Metrics Reference

### API Metrics

| Metric Name | Type | Description | Tags |
|-------------|------|-------------|------|
| `api.request.duration` | Timing | Time taken to process API requests | path, method, status_code |
| `api.request.count` | Counter | Number of API requests | path, method, status_code |
| `api.error.rate` | Counter | Number of API errors | path, method, status_code, error |
| `api.concurrent_requests` | Gauge | Number of requests currently being processed | None |

### Database Metrics

| Metric Name | Type | Description | Tags |
|-------------|------|-------------|------|
| `db.query.duration` | Timing | Time taken to execute database queries | type, operation, database |
| `db.connection_pool.usage.used` | Gauge | Number of used connections in the pool | pool |
| `db.connection_pool.usage.total` | Gauge | Total number of connections in the pool | pool |
| `db.connection_pool.usage.percent` | Gauge | Percentage of connections used | pool |
| `db.query.rows_examined` | Gauge | Number of rows examined by a query | query_type |
| `db.query.rows_returned` | Gauge | Number of rows returned by a query | query_type |
| `db.query.selectivity` | Gauge | Ratio of rows returned to rows examined | query_type |
| `db.vectordb.operation.duration` | Timing | Time taken for vector database operations | type, index, database |

### Algorithm Metrics

| Metric Name | Type | Description | Tags |
|-------------|------|-------------|------|
| `algorithm.matching.duration` | Timing | Time taken for matching algorithms | algorithm |
| `algorithm.path.usage` | Counter | Number of times each algorithm path is used | path, reason |
| `algorithm.match.score.min` | Gauge | Minimum match score | algorithm, path |
| `algorithm.match.score.max` | Gauge | Maximum match score | algorithm, path |
| `algorithm.match.score.mean` | Gauge | Mean match score | algorithm, path |
| `algorithm.match.score.median` | Gauge | Median match score | algorithm, path |
| `algorithm.match.score.stddev` | Gauge | Standard deviation of match scores | algorithm, path |
| `algorithm.match.count` | Gauge | Number of matches returned | algorithm, path, source |
| `algorithm.processing.duration.{stage}` | Timing | Time taken for specific algorithm stages | stage, algorithm |
| `algorithm.match.quality.score` | Gauge | Quality score for a match | match_id |
| `algorithm.match.quality.interaction` | Counter | User interactions with matches | match_id, interaction |

### System Metrics

| Metric Name | Type | Description | Tags |
|-------------|------|-------------|------|
| `system.memory.rss` | Gauge | Resident set size (physical memory used) | None |
| `system.memory.vms` | Gauge | Virtual memory size | None |
| `system.cpu.percent` | Gauge | CPU usage percentage | None |
| `system.files.open` | Gauge | Number of open files | None |
| `system.threads.count` | Gauge | Number of threads | None |
| `system.connections.count` | Gauge | Number of open connections | None |

### Background Task Metrics

| Metric Name | Type | Description | Tags |
|-------------|------|-------------|------|
| `task.execution.duration` | Timing | Time taken to execute background tasks | task, status |
| `task.execution.count` | Counter | Number of background task executions | task, status |

## Dashboard Recommendations

For effective monitoring, we recommend creating dashboards that:

1. **Overview**: Key health metrics (request rate, error rate, response time)
2. **Algorithm Performance**: Match quality, algorithm path usage, processing time
3. **Database Performance**: Query times, connection pool usage 
4. **Resource Utilization**: CPU, memory, connections

## Alerting Recommendations

Consider setting up alerts for:

1. High error rates (> 1% of requests)
2. Slow response times (P95 > 500ms)
3. High connection pool utilization (> 80%)
4. Memory or CPU spikes (> 85% utilization)
5. Low match quality scores (mean < 0.6)

## Troubleshooting with Metrics

When investigating issues:

1. Check API error rates and status codes first
2. Examine algorithm path usage to understand which matching paths are being taken
3. Look at detailed timing metrics for each processing stage
4. Monitor database query complexity and performance
5. Check system resource utilization for bottlenecks

## Adding Custom Metrics

To add custom metrics for specific business needs, use the provided metrics API:

```python
from app.metrics.core import report_timing, report_gauge, increment_counter

# Timing metric
report_timing("custom.operation.duration", duration_in_seconds, {"operation": "name"})

# Gauge metric
report_gauge("custom.measurement", value, {"source": "component"})

# Counter metric
increment_counter("custom.event.count", {"event": "type"})