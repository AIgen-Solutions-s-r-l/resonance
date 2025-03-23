# Detailed Plan for Experience Parameter on /match Endpoints

## Overview
This document outlines the plan to add an "experience" parameter to both the /match and /match/legacy endpoints. The new parameter will be used to prefilter job matches based on experience levels provided.

## 1. Identify Affected Endpoints and Files
- Endpoints: /match and /match/legacy
- Analyze route handlers in the respective service or router modules (e.g., app/services/matching_service.py or app/routers/*)
- Confirm the existing matching logic, likely in app/libs/job_matcher/matcher.py or similar

## 2. Accept and Validate the "experience" Parameter
- Accept an additional optional query parameter named "experience".
- This parameter should be a list of strings with allowed values: "Intern", "Entry", "Mid", "Executive".
- Validate the input and return an error for any invalid value.

## 3. Modify the Matching Logic
- Update matching functions to incorporate the "experience" filter.
- If "experience" is provided (e.g., ["Mid", "Executive"]), filter the MongoDB "resumes" collection:
  - Only include jobs that require one of the specified experience levels.
- Ensure consistent behavior across both endpoints.

## 4. Detailed Logging
- Log the detection of the "experience" filter in the request.
- Log the provided "experience" values and subsequent steps in filtering.
- Ensure comprehensive logging aligned with existing logging practices.

## 5. Update Testing Strategy
- Create new tests to ensure:
  - Valid experience values filter jobs correctly.
  - Invalid values produce appropriate error responses.
- Update existing tests to include scenarios covering the new functionality for both /match and /match/legacy.

## 6. Documentation and API Updates
- Update API documentation, especially in docs/api/ if applicable.
- Include inline comments in the code detailing changes.

## 7. Mermaid Diagram Overview
```mermaid
graph TD
  A[Client Request with optional "experience" parameter] --> B[Route Handler for /match and /match/legacy]
  B --> C[Parameter Parsing & Validation]
  C -- Validates allowed values --> D[Pass parameter to Matching Service]
  D --> E[Matching Service / Job Matcher Module]
  E -- Applies filter based on "experience" --> F[Query MongoDB "resumes" collection]
  F --> G[Return filtered job results]
  G --> H[Detailed logging throughout process]
```

## Next Steps
- Write the plan to a markdown file for documentation.
- Switch to Code mode to implement the changes.