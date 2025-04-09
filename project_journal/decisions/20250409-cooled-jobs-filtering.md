# ADR: Cooled Jobs Filtering Implementation

**Status:** Accepted  
**Date:** 2025-04-09  
**Deciders:** Technical Architect  

## Context

We need to implement a new feature that filters out jobs from the "cooled_jobs" MongoDB collection during the job matching process. The "cooled_jobs" collection contains job IDs that should be excluded from matching results, similar to how jobs that a user has already applied to are filtered out.

The "cooled_jobs" collection has the following structure:
```json
{
  "_id": {
    "$oid": "67f68d47621f40d2919f2926"
  },
  "job_id": "123",
  "timestamp": {
    "$date": "2025-04-09T15:07:51.260Z"
  }
}
```

The current system already has a mechanism to filter out jobs that a user has already applied to using the `AppliedJobsService`, which fetches job IDs from the "already_applied_jobs" MongoDB collection and passes them to the vector matcher.

## Decision

We will create a new `CooledJobsService` class that will be responsible for retrieving job IDs from the "cooled_jobs" MongoDB collection. This service will follow a similar pattern to the existing `AppliedJobsService`.

We will modify the `JobMatcher.process_job` method to fetch cooled job IDs and combine them with applied job IDs before passing them to the vector matcher. The vector matcher will then filter out both sets of job IDs from the matching results.

We will also update the cache key generation to include cooled job IDs to ensure that changes in the "cooled_jobs" collection invalidate the relevant cache entries.

## Alternatives Considered

1. **Extend AppliedJobsService**: Add a new method to the existing `AppliedJobsService` to fetch cooled job IDs. This would require minimal changes to the `JobMatcher` but would violate the single responsibility principle as `AppliedJobsService` would handle two different types of filtering.

2. **Create a JobFilteringService**: Create a new service that handles all job filtering (applied jobs, cooled jobs, etc.). This would be a more elegant long-term solution but would require more extensive refactoring of the existing code.

## Rationale

We chose to create a new `CooledJobsService` for the following reasons:

1. **Clean separation of concerns**: Each service handles one type of filtering, adhering to the single responsibility principle.
2. **Minimal changes to existing code**: We don't need to refactor the `AppliedJobsService` or significantly modify the `JobMatcher`.
3. **Easier testing**: We can test the new service independently without affecting existing functionality.
4. **Faster implementation**: This approach requires the least amount of changes to the existing codebase while still providing a clean solution.

While a more comprehensive `JobFilteringService` would be a better long-term solution, the current approach provides a good balance between clean architecture and implementation efficiency for the immediate requirement.

## Consequences

### Positive

- Clean separation of concerns with each service handling one type of filtering
- Minimal changes to existing code, reducing the risk of introducing bugs
- Follows established patterns in the codebase, making it easier to understand and maintain
- Efficient filtering at the database query level, preventing retrieval of jobs that will be filtered out

### Negative

- Slight duplication of code between `AppliedJobsService` and `CooledJobsService`
- Additional MongoDB query for each job matching request, which could impact performance
- Cache invalidation for existing entries when cooled jobs change

### Mitigations

- Consider implementing caching for cooled job IDs to reduce the performance impact
- Ensure consistent type conversion for job IDs before combining the lists
- Monitor performance and consider implementing a more comprehensive `JobFilteringService` in the future if needed

## Implementation Notes

The implementation will involve:

1. Creating a new `CooledJobsService` class in `app/services/cooled_jobs_service.py`
2. Modifying `JobMatcher.process_job` to fetch cooled job IDs and combine them with applied job IDs
3. Updating the cache key generation to include cooled job IDs
4. Adding appropriate tests for the new functionality

## Related Documents

- [TASK-TA-20250409-172100.md](../tasks/TASK-TA-20250409-172100.md) - Task log for this architectural decision