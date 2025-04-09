# Cooled Jobs Filtering

## Overview

This feature enhances the job recommendation system by filtering out jobs that are in a "cooling period" from user recommendations. This improves the user experience by ensuring they don't see jobs that have been temporarily removed from circulation.

## Implementation Details

### Architecture

The implementation filters out cooled jobs at two levels:

1. **Cache Level**: When retrieving cached job recommendations, the system filters out jobs in the cooling period before returning results.

2. **Search Level**: When performing a new vector search for job recommendations, the system filters out cooled jobs before returning and caching results.

This dual-level approach ensures consistency whether results come from cache or a fresh search.

### Data Flow

```
User Request → Job Matcher → Get Cooled Jobs → Filter Results → Return Filtered Jobs
                   ↓                                     ↑
                Cache Check                        Update Cache
```

### Key Components

1. **CooledJobsService**:
   - Located at: `app/services/cooled_jobs_service.py`
   - Retrieves lists of job IDs that are in the cooling period
   - Interacts with the MongoDB `cooled_jobs` collection

2. **JobMatcher (Modified)**:
   - Located at: `app/libs/job_matcher/matcher.py`
   - Updated to filter out cooled jobs from both cached and fresh search results
   - Updates cache with filtered results to maintain consistency
   - Combines cooled job IDs with applied job IDs for comprehensive filtering

## Performance Considerations

1. **Database Efficiency**:
   - All cooled jobs are retrieved in a single database query
   - The `cooled_jobs` collection should have an index on the `job_id` field

2. **Filtering Efficiency**:
   - Filtering is done with efficient list comprehensions
   - Filtering only occurs if there are cooled jobs

3. **Cache Consistency**:
   - Cache key includes a hash of cooled job IDs to ensure cache invalidation when the cooled jobs list changes
   - Cache is updated with filtered results to prevent showing stale recommendations

## Testing

Tests are implemented in `app/tests/test_cooled_jobs_filtering.py` and cover:

1. Filtering cooled jobs from fresh search results
2. Combining cooled job IDs with applied job IDs
3. Ensuring cache is updated properly with filtered results
4. Verifying cache key generation includes cooled job IDs

## Example

Before filtering:
```json
{
  "jobs": [
    {"id": "job1", "title": "Software Engineer"},
    {"id": "job2", "title": "Data Scientist"},
    {"id": "job3", "title": "Product Manager"},
    {"id": "job4", "title": "UX Designer"}
  ]
}
```

After filtering (if jobs 1 and 3 are in cooling period):
```json
{
  "jobs": [
    {"id": "job2", "title": "Data Scientist"},
    {"id": "job4", "title": "UX Designer"}
  ]
}
```

## Future Improvements

Potential future enhancements could include:

1. Add metrics to track how many jobs are being filtered out due to cooling period
2. Implement a configurable "cooling period" duration
3. Create a comprehensive `JobFilteringService` that handles all types of job filtering (applied, cooled, etc.)
4. Add caching for cooled job IDs to reduce the performance impact of frequent MongoDB queries