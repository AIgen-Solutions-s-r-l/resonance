# Metrics Implementation Plan

## Overview
This plan outlines how to implement basic performance metrics tracking for the matching service, focusing on API response times and matching algorithm performance.

## Current Metrics Infrastructure
Our analysis shows that the service already has a comprehensive metrics system with:

1. **HTTP/API Metrics**
   - Request/response times
   - Status code tracking
   - Slow request identification
   - Request size measurement

2. **Algorithm Performance Metrics**
   - Execution time tracking
   - Match score distribution
   - Result size reporting
   - Error rate tracking

3. **System Metrics**
   - CPU, memory, disk usage
   - Network performance
   - Process stats

4. **Database Metrics**
   - Query performance
   - Connection pool statistics

## Implementation Steps

### 1. Enable Existing Metrics
Ensure the following settings are enabled in your environment or `.env` file:

```
METRICS_ENABLED=True
METRICS_STATSD_ENABLED=True
METRICS_STATSD_HOST=127.0.0.1
METRICS_STATSD_PORT=8125
INCLUDE_TIMING_HEADER=True
```

### 2. Instrument Job Matcher
Ensure the matching algorithm is properly instrumented by applying the decorators to key methods:

```python
# Already implemented in app/metrics/algorithm.py
instrument_job_matcher(job_matcher_instance)
```

### 3. Start the Service
Run the service on port 19001:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 19001
```

### 4. Test with Curl Commands
Test endpoints and verify metrics are being collected:

```bash
# Health check
curl http://localhost:19001/

# Get matched jobs (replace with valid token)
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:19001/jobs/matches
```

### 5. View Metrics
Metrics are being sent to StatsD on localhost:8125. You can:
- Use the simple_statsd_server.py to view metrics
- Or use any StatsD-compatible metric visualization tool

## Key Metrics to Monitor

### API Response Times
- `http.request.duration` - Overall response time for HTTP requests
- `http.routes.duration` - Time spent in specific route handlers

### Matching Algorithm Performance
- `algorithm.duration` - Time spent in matching algorithms
- `algorithm.match_count` - Number of matches found
- `algorithm.score.distribution` - Distribution of match scores
- `algorithm.operation.duration` - Time spent in specific matching operations

## Next Steps
1. Verify metrics are being properly collected
2. Set up alerting for slow operations (if needed)
3. Consider adding custom metrics for specific business needs