# Experience Filter for Match Endpoints

This document describes the `experience` parameter that has been added to both the `/jobs/match` and `/jobs/match/legacy` endpoints.

## Overview

The experience parameter allows clients to prefilter job matches based on experience level requirements. This feature helps users focus their job search on positions that match their career stage or experience level.

## Parameter Details

| Parameter  | Type        | Required | Description                                                  |
|------------|-------------|----------|--------------------------------------------------------------|
| experience | List[str]   | No       | Filter jobs by experience level. Allowed values: Entry-level, Executive-level, Internship, Mid-level, Senior-level |

## Usage

The `experience` parameter can be provided as a query parameter in either the `/jobs/match` or `/jobs/match/legacy` endpoints. When provided, the job matching service will prefilter jobs to only include those that require one of the specified experience levels.

### Example Requests

**Basic Usage:**
```
GET /jobs/match?experience=Mid-level
```

**Multiple Values:**
```
GET /jobs/match?experience=Entry-level&experience=Mid-level
```

**Combined with Other Filters:**
```
GET /jobs/match?experience=Executive-level&country=Germany&keywords=manager
```

## Implementation Details

When the `experience` parameter is provided, the system will:

1. Validate that all values are in the allowed set: "Entry-level", "Executive-level", "Internship", "Mid-level", "Senior-level"
2. Add a SQL filter in the query to the jobs database to only include jobs with matching experience levels
3. Include the experience parameter in cache keys to ensure proper caching
4. Log the experience filter usage for monitoring and debugging purposes

The filter is applied as a prefilter before the vector similarity matching, which reduces the number of jobs that need to be processed and can improve performance when looking for specific experience levels.

## Response Format

The response format is unchanged from the standard match endpoint responses. The `experience` parameter only affects which jobs are included in the matching process, not how the results are returned.

## Error Handling

If invalid experience values are provided, they will be filtered out. If no valid experience values remain, the filter will not be applied.

## Logging

All experience filter usage is logged with detailed information for debugging and monitoring purposes. This includes:
- The values provided in the experience parameter
- Whether the experience filter was applied
- Number of results after filtering

## Example Response

The response format is the same as the standard match endpoints, but will only include jobs matching the specified experience levels:

```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "title": "Senior Software Engineer",
    "workplace_type": "Hybrid",
    "posted_date": "2025-03-01T12:00:00Z",
    "job_state": "Active",
    "description": "We are looking for an experienced software engineer...",
    "short_description": "Senior developer role for our cloud platform",
    "apply_link": "https://apply.example.com/job/123",
    "company_name": "Tech Innovations Inc.",
    "company_logo": "https://assets.example.com/logos/techinnovations.png",
    "city": "Berlin",
    "country": "Germany",
    "portal": "CareerPortal",
    "field": "Information Technology",
    "experience": "Mid-level",
    "skills_required": ["Python", "Docker", "Kubernetes", "FastAPI"]
  }
]
```

## Notes

- For optimal performance, consider using specific experience levels rather than all of them
- The experience filter is combined with other filters (location, keywords) using AND logic
- Within the experience filter, multiple values are combined with OR logic (e.g., "Mid-level" OR "Executive-level")