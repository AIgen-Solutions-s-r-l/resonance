## 2025-03-07 - Metrics Implementation Strategy

**Context:** The matching service needs performance monitoring to understand API response times, database query performance, and matching algorithm efficiency. Currently, the system has limited visibility into these aspects, which makes it difficult to identify bottlenecks and performance issues.

**Decision:** Implement dedicated metrics instrumentation that leverages the existing Datadog integration, focusing on three key areas:
1. API response time metrics via middleware
2. Database query performance metrics via decorated functions/methods
3. Algorithm efficiency metrics for the matching logic

**Rationale:**
- The existing Datadog integration provides a solid foundation to build upon
- A layered metrics approach allows for targeted performance analysis
- Custom instrumentation gives us the flexibility to measure algorithm-specific metrics
- The implementation can be phased, starting with API metrics and expanding to deeper layers

**Implementation:**
1. Create a new metrics module with core functionality
2. Add a FastAPI middleware for API metrics
3. Instrument database operations for query timing
4. Add algorithm-specific metrics to the matching logic
5. Create Datadog dashboards and alerts for visualization

**Consequences:**
- Complete visibility into API response times by endpoint
- Database query performance metrics for identifying slow queries
- Detailed metrics on matching algorithm efficiency
- Ability to detect performance regressions automatically
- Minor performance overhead from metrics collection (expected to be <1%)

## 2025-03-07 - Metrics Implementation Architecture

**Context:** Following the metrics strategy decision, we needed to design and implement the actual metrics system architecture. Key considerations included minimizing overhead, providing a flexible API, supporting multiple backend systems, and ensuring easy adoption across the codebase.

**Decision:** Implement a layered metrics architecture with:
1. A core layer providing generic metrics functionality and backend integrations
2. Domain-specific modules for different aspects of the application (API, database, algorithm)
3. Both decorator-based and direct reporting interfaces

**Rationale:**
- Layered approach allows for separation of concerns and easier maintenance
- Support for multiple backends (StatsD, Datadog) provides flexibility
- Decorator-based approach simplifies common timing use cases
- Direct reporting functions allow for custom metrics reporting
- Domain-specific modules provide tailored metrics for each area

**Implementation:**
1. Created app/metrics/core.py with foundational metrics functions and backends
2. Implemented app/metrics/algorithm.py for algorithm-specific metrics
3. Implemented app/metrics/database.py for database query metrics
4. Implemented app/metrics/middleware.py for API request metrics
5. Used decorator pattern for timing functions and methods
6. Added direct reporting functions for custom metrics
7. Implemented sample rate control to manage overhead
8. Instrumented JobMatcher class with algorithm metrics

**Consequences:**
- Comprehensive metrics system that captures data at all layers
- Low overhead due to sample rate control and efficient implementation
- Easy-to-use API with both decorators and direct reporting
- Support for multiple metrics backends (StatsD, Datadog)
- Unified approach to metrics across the codebase
- Better visibility into performance bottlenecks
- Potential for future expansion to additional metrics types and backends

## 2026-02-26 - Job ID Type Change from String to UUID

**Context:** Currently, the `id` field in JobSchema is defined as a string even though it represents a UUID. The database model generates UUIDs but stores them as strings: `id: str = Column(String, primary_key=True, default=lambda: str(uuid4()))`. This leads to a mismatch between the actual data type (UUID) and how it's represented in the schema (string).

**Decision:** Change the JobSchema `id` field type from string to UUID to accurately reflect its nature while maintaining compatibility with the database storage.

**Rationale:**
- Using the correct data type (UUID) in the schema improves type safety and makes the API contract more accurate
- Pydantic can handle the serialization/deserialization between UUID objects and string representations automatically
- This change helps prevent errors where non-UUID strings might be incorrectly accepted as valid IDs
- The change is backward compatible as the string representation will still be the same in JSON responses

**Implementation:**
1. Update JobSchema in app/schemas/job.py to import UUID from the uuid module
2. Change the type annotation of the `id` field from `str` to `UUID`
3. No changes needed to the database model as it will continue to store the string representation

**Consequences:**
- More accurate type information in the schema
- Improved validation for UUID fields
- No breaking changes to the API as UUIDs serialize to the same string format
- Better alignment between the conceptual data model and its implementation

## 2026-02-27 - Revert Job ID Type from UUID to String with Validation

**Context:** After implementing the UUID type for the `id` field in JobSchema, we encountered compatibility issues with MongoDB, which doesn't natively support Python's UUID type. While the SQL database was handling the UUID conversion correctly, MongoDB was raising errors when processing UUID objects.

**Decision:** Change the JobSchema `id` field back to string type but add explicit validation to ensure it still adheres to the UUID format.

**Rationale:**
- MongoDB has compatibility issues with Python's UUID objects
- String representation is more universally compatible across different database systems
- We can maintain type safety by adding explicit validation via Pydantic field validators
- This approach gives us the best of both worlds: database compatibility and type validation

**Implementation:**
1. Update JobSchema in app/schemas/job.py to use `str` type for the `id` field
2. Add a Pydantic field validator to ensure the string follows UUID format
3. Tests confirm the validation works correctly and rejects non-UUID strings

**Consequences:**
- Better compatibility with MongoDB while maintaining data integrity
- Explicit validation ensures only properly formatted UUIDs are accepted
- No breaking changes to the API as the format remains the same
- Type safety is preserved through validation rather than the type system

## 2025-03-07 - Match Count Metrics Implementation

**Context:** While we have metrics for match quality (score distributions) and algorithm performance (timing), we lack visibility into the quantity of matches being returned. This information is crucial for understanding service effectiveness, identifying potential issues with filtering logic, and ensuring we're providing sufficient matches to users.

**Decision:** Implement a dedicated report_match_count function to track the number of matches returned by different algorithm paths, and expose this metric through our metrics API.

**Rationale:**
- Match count is a fundamental indicator of service health and effectiveness
- Different algorithm paths may produce varying quantities of matches
- This metric will help us understand how filtering parameters affect match volume
- Combined with score distribution metrics, this provides a more complete picture of match quality and quantity

**Implementation:**
1. Added ALGORITHM_MATCH_COUNT to MetricNames in core.py
2. Created report_match_count function in algorithm.py
3. Updated __init__.py to expose the new function
4. Added the function to job_matcher.py on both algorithm paths
5. Added corresponding test in test_metrics.py
6. Updated demo_metrics.py to demonstrate the new functionality
7. Updated metrics documentation to include the new metric

**Consequences:**
- Better visibility into match volume across different algorithm paths
- Ability to monitor match quantity trends over time
- Capacity to detect anomalies in match generation
- More comprehensive metrics dashboard
- Foundation for potential SLAs around minimum match counts

## 2025-03-07 - Metrics Testing Compatibility Improvements

**Context:** While implementing and testing the metrics system, we encountered inconsistencies in how tags were being handled between the production code and test mocks. This caused tests to fail even though the functionality was working correctly in production. The specific issue was that our test assertions expected tags to be passed as a keyword argument named "tags", but our implementation was passing them as a positional argument.

**Decision:** Enhance the metrics backend implementation to support both positional and keyword arguments for tags, and ensure consistent tag formatting for test verification.

**Rationale:**
- Test compatibility is essential for ensuring metrics are being reported correctly
- Supporting both argument styles provides flexibility and backward compatibility
- Consistent tag formatting makes test assertions more reliable and easier to write
- This approach maintains the production code's behavior while improving testability

**Implementation:**
1. Updated the MetricsBackend base class to accept both positional and keyword arguments for tags
2. Modified the StatsD and DogStatsD backend implementations to handle both argument styles
3. Updated the report_timing, report_gauge, and increment_counter functions to format tags consistently
4. Modified tag formatting to ensure a standardized format (list of "key:value" strings) for test verification
5. Ran tests to confirm all metrics functions now work correctly with test mocks

**Consequences:**
- All metrics tests now pass consistently
- Better test coverage for metrics functionality
- More reliable tag handling across different metrics backends
- Improved flexibility in how metrics can be reported
- Easier maintenance and testing of metrics code in the future

## 2025-03-09 - JWT Error Handling Improvement

**Context:** The application was logging full stack traces for JWT authentication errors, which made the logs verbose and potentially exposed sensitive information. The error was occurring because the application was using a placeholder secret key "your-secret-key-here" for JWT validation.

**Decision:** Improve the JWT error handling to log concise error messages without full stack traces while maintaining the existing authentication behavior.

**Rationale:**
- Full stack traces in logs can expose implementation details that shouldn't be public
- More concise error messages make logs easier to read and analyze
- Capturing the essential error information without the stack trace still provides necessary debugging context
- The placeholder secret key was intended to be used in the current environment

**Implementation:**
1. Modified `app/core/auth.py` to use `logger.error()` instead of `logger.exception()` for JWT validation errors
2. Updated `app/core/security.py` to use `logger.error()` with the specific error message for token decoding issues
3. Added the error message text to the error logs to maintain the necessary context
4. Preserved the existing authentication flow and validation logic

**Consequences:**
- Cleaner log output with focused error information
- Reduced verbosity in logs while maintaining necessary context
- Better security by not exposing the full stack trace
- Improved readability of logs for operations and debugging
- No changes to the authentication behavior or security model

## 2025-03-09 - In-Memory Caching Implementation for Job Matching

**Context:** The matching service performs computationally expensive vector similarity searches that can be redundant when users make identical queries in a short time period. This creates unnecessary database load and increases response times for repeated queries.

**Decision:** Implement an in-memory caching system within the OptimizedJobMatcher class that stores job matching results for 5 minutes, using a combination of query parameters as cache keys.

**Rationale:**
- Vector similarity searches are CPU and database intensive
- Many users may request the same job matches within a short timeframe
- In-memory caching provides significant performance benefits without complex external dependencies
- Time-based expiration ensures results don't become stale
- Size-based limits prevent memory issues

**Implementation:**
1. Created an in-memory dictionary cache in job_matcher_optimized.py using the pattern `{cache_key: (result, timestamp)}`
2. Implemented cache key generation based on resume ID, location filters, keyword filters, and pagination offset
3. Added cache lookup before database queries and cache storage after successful queries
4. Set TTL to 300 seconds (5 minutes) to balance freshness and performance
5. Added size-based pruning that removes the oldest entries when the cache exceeds 1000 items
6. Used asyncio.Lock() to ensure thread safety for cache operations

**Consequences:**
- Significantly reduced database load for repeated matching requests
- Improved response times for cached queries
- No external dependencies required (such as Redis)
- Lightweight implementation with minimal overhead
- Cache is not shared across instances (limitation for distributed deployments)
- Cache entries expire after 5 minutes regardless of access frequency
- No mechanism to manually invalidate cache when job data changes (relies on TTL)

## Template for Future Decisions

## [Date] - [Decision Topic]
**Context:** [What led to this decision point? What problem are we solving?]
**Decision:** [What was decided?]
**Rationale:** [Why was this decision made? What alternatives were considered?]
**Implementation:** [How the decision will be/was implemented]
**Consequences:** [Expected impacts, both positive and negative]