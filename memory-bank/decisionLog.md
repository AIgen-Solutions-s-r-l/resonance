## 2026-02-26 - Enhanced Authentication Debugging

**Context:** The API was returning 401 Unauthorized errors when accessing the `/jobs/match` endpoint. The existing error handling provided limited diagnostic information, making it difficult to identify the specific cause of authentication failures, such as expired tokens, invalid signatures, or malformed headers.

**Decision:** Enhance the authentication debugging capabilities by:
1. Adding more specific error handling and logging in the authentication process
2. Implementing a new middleware to log detailed information about authentication attempts
3. Improving the token verification function documentation and options
4. Providing different error messages based on specific JWT error types

**Rationale:**
- Generic 401 errors without specific context make troubleshooting difficult
- Authentication issues are among the most common API problems and can impact client applications
- Detailed logging of authentication attempts helps identify patterns of failures
- Specific error messages help both developers and API consumers diagnose issues faster

**Implementation:**
- Modified `get_current_user` in app/core/auth.py to catch specific JWT exception types
- Added detailed logging throughout the authentication process
- Updated the token verification function with explicit verification options
- Created an AuthDebugMiddleware in app/main.py to intercept and log authentication attempts

**Consequences:**
- More comprehensive logging will make authentication issues easier to diagnose
- Logs may contain sensitive information and should be properly secured
- Slightly increased overhead due to additional logging and token decoding
- Improved developer experience when troubleshooting authentication problems
- Foundation for more advanced authentication metrics and monitoring

## 2026-02-26 - JobSchema Field Type and Name Changes

**Context:** After the recent field removal, several additional improvements to the JobSchema were identified to enhance clarity and correctness. Specifically, the `id` field should be an integer to match its actual data type, and the `company` and `logo` fields needed to be renamed for better semantic clarity.

**Decision:**
1. Change the `id` field type from string to integer
2. Rename the `logo` field to `company_logo`
3. Rename the `company` field to `company_name`

**Rationale:**
- The `id` field is actually stored as an integer in the database, so the schema should reflect this for consistency and proper typing
- The `logo` field specifically refers to a company logo, so `company_logo` is more descriptive and clear
- The `company` field contains a company name, so `company_name` is more precise and reduces ambiguity

**Implementation:**
- Update the JobSchema in app/schemas/job.py with the new field types and names
- Modify the JobMatcher class to output the new field names in job dictionaries
- Update test cases to verify that the changes don't break existing functionality
- Document the changes in the Memory Bank

**Consequences:**
- API consumers will need to adapt to the new field names and the integer id type
- More consistent and semantically clear API responses
- Better type safety with the integer id field
- Potential need to update from_orm field mapping in jobs_matched_router.py

## 2026-02-26 - Removing Unused Fields from JobSchema

**Context:** The `/match` endpoint returns several fields in the JobSchema that are not needed by clients and may expose unnecessary implementation details. These fields include: job_id, company_id, location_id, cluster_id, processed_description, embedding, and sparse_embeddings.

**Decision:** Remove these fields from the JobSchema response model while keeping them in the underlying database model. This will reduce payload size and prevent exposing implementation details that are only used internally.

**Rationale:**
- The `embedding` and `sparse_embeddings` fields are used for similarity calculations internally but aren't needed in API responses
- `company_id`, `location_id`, and `cluster_id` are database relationship identifiers not needed by API consumers
- `job_id` appears redundant with `id` (both are returned in the API)
- `processed_description` is an internal field not needed in the response

**Implementation:**
- Modify the JobSchema in app/schemas/job.py to remove these fields
- Keep the database model (Job class) unchanged as these fields are needed for internal operations
- Ensure the API response model is still valid and maintains backward compatibility for critical fields
- Test the `/match` endpoint to verify it continues to function correctly
# Decision Log: Matching Service

This log maintains a record of key architectural and design decisions made throughout the project lifecycle, providing context and rationale for future reference.

## February 26, 2025 - Memory Bank Initialization
**Context:** Need for centralized architectural documentation and tracking for the Matching Service project.
**Decision:** Implemented Memory Bank system with core files for tracking context, progress, and decisions.
**Rationale:** A structured approach to documentation helps maintain project knowledge, facilitates onboarding, and ensures consistent architecture evolution.
**Implementation:** Created memory-bank directory with core files (productContext.md, activeContext.md, progress.md, decisionLog.md, systemPatterns.md).

## Template for Future Decisions

## [Date] - [Decision Topic]
**Context:** [What led to this decision point? What problem are we solving?]
**Decision:** [What was decided?]
**Rationale:** [Why was this decision made? What alternatives were considered?]
**Implementation:** [How the decision will be/was implemented]
**Consequences:** [Expected impacts, both positive and negative]