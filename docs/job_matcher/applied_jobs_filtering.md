# Applied Jobs Filtering

## Overview

This feature enhances the job recommendation system by filtering out jobs that a user has already applied for from their recommendations. This improves the user experience by ensuring they don't see the same jobs repeatedly after applying.

## Implementation Details

### Architecture

The implementation filters out applied jobs at two levels:

1. **Cache Level**: When retrieving cached job recommendations, the system filters out jobs the user has already applied for before returning results.

2. **Search Level**: When performing a new vector search for job recommendations, the system filters out applied jobs before returning and caching results.

This dual-level approach ensures consistency whether results come from cache or a fresh search.

### Data Flow

```
User Request → Job Matcher → Get Applied Jobs → Filter Results → Return Filtered Jobs
                   ↓                                     ↑
                Cache Check                        Update Cache
```

### Key Components

1. **AppliedJobsService**:
   - Located at: `app/services/applied_jobs_service.py`
   - Retrieves lists of job IDs a user has already applied for
   - Interacts with the MongoDB `already_applied_jobs` collection

2. **JobMatcher (Modified)**:
   - Located at: `app/libs/job_matcher/matcher.py`
   - Updated to filter out applied jobs from both cached and fresh search results
   - Updates cache with filtered results to maintain consistency

## Performance Considerations

1. **Database Efficiency**:
   - All applied jobs are retrieved in a single database query
   - The `already_applied_jobs` collection should have an index on the `user_id` field

2. **Filtering Efficiency**:
   - Filtering is done with efficient list comprehensions
   - Filtering only occurs if the user has applied jobs

3. **Cache Consistency**:
   - Cache is updated with filtered results to prevent showing stale recommendations

## Testing

Tests are implemented in `app/tests/test_applied_jobs_filtering.py` and cover:

1. Filtering applied jobs from fresh search results
2. Filtering applied jobs from cached results
3. Ensuring cache is updated properly with filtered results

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

After filtering (if user applied to job1 and job3):
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

1. Add metrics to track how many jobs are being filtered out
2. Implement a configurable "time window" for filtering (e.g., don't show jobs applied for in the last 30 days)
3. Add an option for users to reset their applied jobs filter