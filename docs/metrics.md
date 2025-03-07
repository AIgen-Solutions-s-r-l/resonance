# Matching Service Metrics System

## Overview

The matching service includes a comprehensive metrics system that provides visibility into API performance, database operations, and matching algorithm efficiency. This document explains how to use, configure, and extend the metrics system.

## Metrics Architecture

The metrics system is built as a layered architecture:

1. **Core Metrics**: Foundation for all metrics functionality
2. **API Metrics**: Request timing, counting, and error tracking
3. **Database Metrics**: Query performance and connection pool monitoring
4. **Algorithm Metrics**: Matching algorithm performance metrics

## Configuration

Configure the metrics system using these environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `METRICS_ENABLED` | Enable/disable metrics collection | `True` |
| `METRICS_SAMPLE_RATE` | Percentage of operations that generate metrics (0.0-1.0) | `1.0` |
| `METRICS_HOST` | StatsD/DogStatsD host | `127.0.0.1` |
| `METRICS_PORT` | StatsD/DogStatsD port | `8125` |
| `DD_API_KEY` | Datadog API key (optional) | - |
| `DD_APP_KEY` | Datadog application key (optional) | - |

## Using Metrics in Your Code

### Timing Function Execution

Use decorators to time function execution:

```python
from app.metrics import timer, async_timer

@timer("my.function.duration", {"component": "my_module"})
def my_function():
    # Function code here
    
@async_timer("my.async_function.duration", {"component": "my_module"})
async def my_async_function():
    # Async function code here
```

### Timing Code Blocks

Use context managers to time specific blocks of code:

```python
from app.metrics import Timer

def my_function():
    # Some code
    
    with Timer("my.operation.duration", {"operation": "data_processing"}):
        # Code to time
        process_data()
```

### Reporting Metrics Directly

Use reporting functions for direct metrics reporting:

```python
from app.metrics import report_timing, report_gauge, increment_counter

# Report timing metric
report_timing("api.custom.operation", 0.153, {"operation": "validation"})

# Report gauge value
report_gauge("cache.size", cache.size(), {"cache": "user_data"})

# Increment counter
increment_counter("api.request.count", {"endpoint": "jobs"})
```

### Database Metrics

Use database-specific decorators for query timing:

```python
from app.metrics.database import sql_query_timer, mongo_operation_timer

@sql_query_timer("select", "get_jobs")
def get_jobs_from_db(cursor, params):
    # Database query code
    
@mongo_operation_timer("find", "job_matches")
def find_job_matches(query):
    # MongoDB query code
```

### Algorithm Metrics

Use algorithm-specific functions for matching algorithms:

```python
from app.metrics.algorithm import (
    matching_algorithm_timer,
    report_match_score_distribution,
    report_algorithm_path,
    report_match_count
)

@matching_algorithm_timer("vector_similarity")
def match_with_vector_similarity(resume, jobs):
    # Algorithm code
    
    # Report which algorithm path was used
    report_algorithm_path("cosine_distance", {"reason": "better_for_sparse_vectors"})
    
    # Report score distribution
    scores = [job.score for job in matched_jobs]
    report_match_score_distribution(scores, {"algorithm": "vector_similarity"})
    
    # Report match count
    report_match_count(len(matched_jobs), {"algorithm": "vector_similarity"})
```

## API Metrics

The FastAPI middleware automatically collects these metrics for all API requests:

- Request duration by endpoint and method
- Request count by endpoint and method
- Error rate by endpoint, method, and status code
- Concurrent request count

The middleware normalizes high-cardinality paths (e.g., `/jobs/123` → `/jobs/{id}`) to prevent metric explosion.

## Available Metrics

| Metric Name | Type | Description |
|-------------|------|-------------|
| `api.request.duration` | Timing | API request duration in seconds |
| `api.request.count` | Counter | API request count |
| `api.error.rate` | Counter | API error count |
| `api.concurrent_requests` | Gauge | Currently active API requests |
| `db.query.duration` | Timing | Database query duration |
| `db.connection_pool.usage` | Gauge | Connection pool utilization |
| `db.vectordb.operation.duration` | Timing | Vector database operation duration |
| `algorithm.matching.duration` | Timing | Matching algorithm execution time |
| `algorithm.path.usage` | Counter | Algorithm path selection count |
| `algorithm.match.score` | Gauge | Match score metrics |
| `algorithm.match.count` | Gauge | Number of matches found |
| `algorithm.processing.duration` | Timing | Processing step duration |

## Common Tags

Tags provide additional context for metrics. Common tags include:

| Tag | Description | Example Values |
|-----|-------------|---------------|
| `method` | HTTP method | `GET`, `POST` |
| `path` | API endpoint path | `/jobs`, `/jobs/{id}` |
| `status_code` | HTTP status code | `200`, `404`, `500` |
| `algorithm` | Algorithm name | `vector_similarity`, `keyword_matching` |
| `operation` | Operation name | `skill_extraction`, `embedding_generation` |
| `database` | Database name | `postgres`, `mongodb` |
| `type` | Operation type | `select`, `insert`, `update` |

## Performance Considerations

The metrics system is designed to minimize overhead:

- Sample rate control allows tuning metrics volume
- Metrics can be completely disabled in production if needed
- Fast path when metrics are disabled skips all overhead
- Efficient tag handling reduces memory allocations

## Extending the Metrics System

To add new metrics:

1. Add new metric names to `app.metrics.core.MetricNames`
2. Create specialized functions or decorators in the appropriate module
3. Update the `__init__.py` exports if needed

For major extensions, add a new domain-specific module (e.g., `cache_metrics.py`).

## Dashboards and Alerts

The metrics system integrates with Datadog for visualization and alerting. Key dashboards include:

1. **API Performance Dashboard**
   - Endpoint response times
   - Request volumes
   - Error rates
   - Concurrent requests

2. **Database Performance Dashboard**
   - Query duration by type
   - Connection pool usage
   - Query volumes

3. **Algorithm Performance Dashboard**
   - Algorithm execution time
   - Match score distributions
   - Algorithm path usage
   - Match counts

## Troubleshooting

If metrics are not appearing:

1. Verify `METRICS_ENABLED` is set to `True`
2. Check `METRICS_HOST` and `METRICS_PORT` configuration
3. Ensure the StatsD/DogStatsD server is running
4. Increase log level to `DEBUG` to see detailed metrics logs