# Field Removal Plan for `/match` Endpoint

## Fields to Remove
- job_id
- company_id
- location_id
- cluster_id
- processed_description
- embedding
- sparse_embeddings

## Implementation Plan

### 1. Backup Current Schema
Before making any changes, we'll create a backup of the current schema to ensure we can roll back if needed.

### 2. Modify JobSchema
Update the JobSchema in `app/schemas/job.py` to remove the specified fields.

### 3. Test `/match` Endpoint
Test the `/match` endpoint to verify that it still functions correctly without the removed fields.

### 4. Test Related Functionality
Check if any related functionality (like quality tracking or other endpoints) might be affected by this change.

### 5. Roll Back Plan
In case of issues, we'll have a rollback plan ready to revert to the original schema.

## Technical Details

### Current Implementation
- The `/match` endpoint returns a list of `JobSchema` objects
- `JobSchema` is converted from the raw job dictionaries using `.from_orm()`
- The actual job matching logic uses `embedding` and other fields internally, but they aren't needed in the response

### Safety Considerations
- Database model (`app/models/job.py`) will remain unchanged as these fields are still needed for internal operations
- Only the API response schema will be modified
- The SQL queries in `JobMatcher` that use `embedding` for similarity calculations will continue to work

## Testing Strategy
1. Unit tests for the modified schema
2. Integration tests for the `/match` endpoint
3. Manual testing of the API response
4. Verify no downstream services are broken

## Implementation Steps
1. Create a backup branch
2. Modify JobSchema
3. Run tests
4. Deploy to staging
5. Verify functionality
6. Deploy to production