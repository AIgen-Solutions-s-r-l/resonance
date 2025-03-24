# Testing Experience Filter with Legacy Matching

This document explains how to test whether the experience filter is correctly applied in the legacy matching endpoint.

## Overview

The matching service should apply an experience filter when the `experience` query parameter is provided. This test verifies that:

1. The request correctly includes the experience filter
2. The backend applies the filter to the matching query
3. The logs show evidence of the experience filter being applied

## Setup

1. Make sure the test script is executable:
   ```bash
   chmod +x tools/test_experience_filter.sh
   ```

2. If needed, modify the `TOKEN` variable in the script to use a valid authentication token.

## Testing Process

### 1. Start the Matching Service

In one terminal, start the matching service with debug logging:

```bash
uvicorn app.main:app --reload --port 9001 --log-level debug
```

### 2. Run the Test Script

In another terminal, run the test script:

```bash
./tools/test_experience_filter.sh
```

This will display curl commands for testing. Copy and run these commands.

### 3. Analyze the Logs

After running the curl commands, analyze the server logs to verify that:

1. The experience filter parameters are correctly received
2. The prefilter is being applied

#### What to Look For in the Logs

1. **Request Reception**:
   - Look for log entries like: `User {current_user} is requesting matched jobs (legacy endpoint)`
   - Verify the experience parameters are included

2. **Query Construction**:
   - Look for entries related to `_build_experience_filters` or similar functions
   - Check for SQL conditions being constructed with experience filters

3. **Query Execution**:
   - Look for the final SQL query being executed
   - Verify it includes conditions like `j.experience = 'senior'`

4. **Result Filtering**:
   - Check if the jobs in the response have the requested experience levels

## Troubleshooting

If the experience filter isn't being applied:

1. Check if the experience parameter is correctly passed in the URL
2. Verify the query builder is constructing the right SQL conditions
3. Examine any error messages in the logs

## Example Log Patterns

When the experience filter is working correctly, you should see logs similar to:

```
DEBUG:app.libs.job_matcher.query_builder:Building experience filters: ['senior']
DEBUG:app.libs.job_matcher.query_builder:Added experience condition: (j.experience = %s)
DEBUG:app.libs.job_matcher.vector_matcher:Executing query with experience filter
```

If these patterns are present, it confirms the experience filter is being correctly applied as a prefilter.