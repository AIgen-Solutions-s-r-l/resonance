# Matching Service Metrics Guide

This document provides a comprehensive overview of the metrics collected by the matching service, how to set up and configure metrics collection, and how to interpret metrics for monitoring performance, diagnosing issues, and improving service quality.

## Setup and Configuration

### Quick Start

To quickly get started with metrics:

1. Configure metrics in your `.env` file:
   ```
   METRICS_ENABLED=True
   METRICS_STATSD_ENABLED=True
   METRICS_STATSD_HOST=127.0.0.1
   METRICS_STATSD_PORT=8125
   ```

2. Run the local StatsD server:
   ```bash
   python simple_statsd_server.py --verbose
   ```

3. Start your application:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 19001
   ```

4. Monitor metrics in the StatsD server terminal

### Available Metrics Backends

The service supports multiple metrics backends that can be configured via environment variables:

#### 1. StatsD Backend

The StatsD backend sends metrics to a StatsD server over UDP.

**Configuration:**
```
METRICS_ENABLED=True
METRICS_STATSD_ENABLED=True
METRICS_STATSD_HOST=127.0.0.1
METRICS_STATSD_PORT=8125
STATSD_USE_TAGS=True
```

**Running the local StatsD server:**

For development and testing, use the included simple StatsD server:

```bash
# Basic usage
python simple_statsd_server.py

# With verbose output
python simple_statsd_server.py --verbose

# With custom host/port
python simple_statsd_server.py --host 0.0.0.0 --port 8125

# With output to file
python simple_statsd_server.py --output-file metrics.log

# Help
python simple_statsd_server.py --help
```

The StatsD server will display metrics every 10 seconds and when you terminate the server.

#### 2. Prometheus Backend

The Prometheus backend exposes metrics via an HTTP endpoint for scraping.

**Configuration:**
```
METRICS_ENABLED=True
METRICS_PROMETHEUS_ENABLED=True
METRICS_PROMETHEUS_PORT=9091
PROMETHEUS_STANDALONE=True  # Set to True to run a standalone HTTP server
```

When configured, metrics will be available at `http://localhost:9091/metrics`.

#### 3. DataDog Integration

For production monitoring, you can configure DataDog integration:

**Configuration:**
```
METRICS_ENABLED=True
METRICS_STATSD_ENABLED=True
METRICS_STATSD_HOST=127.0.0.1
METRICS_STATSD_PORT=8125
DD_API_KEY=your-datadog-api-key
DD_APP_KEY=your-datadog-app-key
```

### Testing Metrics Collection

Use the included test scripts to verify metrics collection:

1. **Run a simple metrics test:**
   ```bash
   python test_metrics_simple.py
   ```

2. **Run the full metrics test suite:**
   ```bash
   # Make the script executable first
   chmod +x run_metrics_test.sh
   
   # Run the test script
   ./run_metrics_test.sh
   ```

### All Metrics Configuration Options

| Environment Variable | Default | Description |
|----------------------|---------|-------------|
| `METRICS_ENABLED` | `True` | Master switch to enable/disable metrics |
| `METRICS_DEBUG` | `False` | Enable verbose logging of metrics |
| `METRICS_PREFIX` | `matching_service` | Prefix for all metrics |
| `METRICS_SAMPLE_RATE` | `1.0` | Sampling rate (0.0-1.0) for metrics |
| `METRICS_COLLECTION_ENABLED` | `True` | Enable periodic metrics collection |
| `INCLUDE_TIMING_HEADER` | `False` | Include timing info in HTTP responses |
| `METRICS_STATSD_ENABLED` | `True` | Enable StatsD backend |
| `METRICS_STATSD_HOST` | `127.0.0.1` | StatsD server host |
| `METRICS_STATSD_PORT` | `8125` | StatsD server port |
| `METRICS_PROMETHEUS_ENABLED` | `False` | Enable Prometheus backend |
| `METRICS_PROMETHEUS_PORT` | `9091` | Prometheus server port |
| `SYSTEM_METRICS_ENABLED` | `True` | Enable system metrics collection |
| `SYSTEM_METRICS_INTERVAL` | `60` | System metrics collection interval (seconds) |
| `SLOW_REQUEST_THRESHOLD_MS` | `1000.0` | Threshold to log slow HTTP requests (ms) |
| `SLOW_QUERY_THRESHOLD_MS` | `500.0` | Threshold to log slow DB queries (ms) |
| `SLOW_OPERATION_THRESHOLD_MS` | `2000.0` | Threshold to log slow operations (ms) |

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
- **Prometheus**: Metrics collection for Prometheus-based monitoring

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
```

## Advanced Usage

### Decorator-based Metrics

For timing function executions, use the provided decorators:

```python
from app.metrics import timer, matching_algorithm_timer, sql_query_timer

# Basic timing decorator
@timer("my.function.duration")
def my_function():
    # Function body...
    pass

# Algorithm-specific decorator
@matching_algorithm_timer("vector_similarity")
def my_matching_algorithm():
    # Algorithm implementation...
    pass

# Database query timing
@sql_query_timer("SELECT")
def execute_query():
    # Query execution...
    pass
```

### Context Manager

For timing code blocks:

```python
from app.metrics import Timer

with Timer("my.operation.duration", {"operation": "custom"}):
    # Code to time
    pass