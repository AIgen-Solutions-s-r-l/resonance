# Jobs Details Endpoint

The `/jobs/details` endpoint allows you to retrieve detailed information for multiple jobs by their IDs in a single request. This endpoint is useful when you have collected job IDs from other endpoints and need to obtain the complete details for these jobs.

## Overview

The "jobs/details" endpoint provides a way to efficiently retrieve detailed information for multiple jobs by their unique identifiers (UUIDs) in a single API call. This is particularly useful in scenarios where you have obtained job IDs from other endpoints (such as search or matching endpoints) and need to display comprehensive job information to users.

**Key Features:**
- Batch retrieval of multiple jobs in a single request
- Comprehensive job details including company and location information
- Automatic filtering of invalid job IDs
- Structured response format with consistent fields

## Authentication

This endpoint requires API key authentication. You must include the `api-key` header with a valid API key.

**Header Example:**
```
api-key: your-api-key-here
```

If you provide an invalid or missing API key, the server will respond with a 401 Unauthorized status code.

## Request Format

- **HTTP Method:** GET
- **URL:** `/jobs/details`
- **Required Headers:**
  - `api-key`: Your API authentication key

## Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| job_ids | List[str] | No | List of job IDs (UUIDs) to retrieve details for |

### job_ids Format
The `job_ids` parameter accepts a list of UUID strings. Each UUID must be in the standard format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` (where `x` is a hexadecimal digit).

**Example Query:**
```
/jobs/details?job_ids=123e4567-e89b-12d3-a456-426614174000&job_ids=123e4567-e89b-12d3-a456-426614174001
```

**Notes:**
- If no `job_ids` are provided, the endpoint will return an empty result with status "success"
- Invalid UUIDs in the request will be automatically filtered out
- The system will log a warning if invalid UUIDs are provided, but will not return an error

## Response Structure

The response is a JSON object conforming to the `JobDetailResponse` schema:

```json
{
  "jobs": [
    {
      "id": "string",
      "title": "string",
      "workplace_type": "string",
      "posted_date": "datetime",
      "job_state": "string",
      "description": "string",
      "apply_link": "string",
      "company_name": "string",
      "company_logo": "string",
      "location": "string",
      "city": "string",
      "country": "string",
      "portal": "string",
      "short_description": "string",
      "field": "string",
      "experience": "string",
      "score": "float",
      "skills_required": ["string"]
    }
  ],
  "count": 0,
  "status": "string"
}
```

### Field Descriptions

#### Root Level Fields
| Field | Type | Description |
|-------|------|-------------|
| jobs | Array | List of job objects matching the requested IDs |
| count | Integer | Number of jobs returned |
| status | String | Status of the request (e.g., "success") |

#### Job Object Fields
| Field | Type | Description |
|-------|------|-------------|
| id | String | Unique identifier (UUID) for the job |
| title | String | Job title |
| workplace_type | String | Type of workplace (e.g., "Remote", "On-site", "Hybrid") |
| posted_date | DateTime | When the job was posted |
| job_state | String | Current state of the job listing (e.g., "Active", "Closed") |
| description | String | Full job description |
| short_description | String | Brief summary of the job |
| apply_link | String | URL to apply for the job |
| company_name | String | Name of the company offering the job |
| company_logo | String | URL to the company's logo image |
| location | String | General location information |
| city | String | City where the job is located |
| country | String | Country where the job is located |
| portal | String | Source job portal |
| field | String | Professional field or industry |
| experience | String | Required experience level |
| score | Float | Relevance or matching score (if applicable) |
| skills_required | Array of Strings | List of skills required for the job |

## Error Responses

| Status Code | Description | Possible Cause |
|-------------|-------------|---------------|
| 401 | Unauthorized | Invalid or missing API key |
| 500 | Internal Server Error | Database error or other server-side issue |

### Error Response Format

```json
{
  "detail": "Error message description"
}
```

## Usage Examples

### Example 1: Retrieve a Single Job

**Request:**
```bash
curl -X GET "https://api.example.com/jobs/details?job_ids=123e4567-e89b-12d3-a456-426614174000" \
  -H "api-key: your-api-key-here"
```

**Successful Response (200 OK):**
```json
{
  "jobs": [
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
      "experience": "5+ years",
      "skills_required": ["Python", "Docker", "Kubernetes", "FastAPI"]
    }
  ],
  "count": 1,
  "status": "success"
}
```

### Example 2: Retrieve Multiple Jobs

**Request:**
```bash
curl -X GET "https://api.example.com/jobs/details?job_ids=123e4567-e89b-12d3-a456-426614174000&job_ids=123e4567-e89b-12d3-a456-426614174001" \
  -H "api-key: your-api-key-here"
```

**Successful Response (200 OK):**
```json
{
  "jobs": [
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
      "experience": "5+ years",
      "skills_required": ["Python", "Docker", "Kubernetes", "FastAPI"]
    },
    {
      "id": "123e4567-e89b-12d3-a456-426614174001",
      "title": "Data Scientist",
      "workplace_type": "Remote",
      "posted_date": "2025-03-02T14:30:00Z",
      "job_state": "Active",
      "description": "Seeking a data scientist to analyze large datasets...",
      "short_description": "Data science role focused on machine learning",
      "apply_link": "https://apply.example.com/job/124",
      "company_name": "Data Analysis Corp",
      "company_logo": "https://assets.example.com/logos/dataanalysis.png",
      "city": "Munich",
      "country": "Germany",
      "portal": "JobBoard",
      "field": "Data Science",
      "experience": "3+ years",
      "skills_required": ["Python", "SQL", "Machine Learning", "TensorFlow"]
    }
  ],
  "count": 2,
  "status": "success"
}
```

### Example 3: No Job IDs Provided

**Request:**
```bash
curl -X GET "https://api.example.com/jobs/details" \
  -H "api-key: your-api-key-here"
```

**Successful Response (200 OK):**
```json
{
  "jobs": [],
  "count": 0,
  "status": "success"
}
```

### Example 4: Invalid API Key

**Request:**
```bash
curl -X GET "https://api.example.com/jobs/details?job_ids=123e4567-e89b-12d3-a456-426614174000" \
  -H "api-key: invalid-key"
```

**Error Response (401 Unauthorized):**
```json
{
  "detail": "Invalid API key"
}
```

## Implementation Details

The endpoint validates all job IDs to ensure they are in UUID format and filters out invalid IDs before querying the database. This ensures that malformed requests won't cause errors but will still return valid results for any correctly formatted IDs.

The response includes comprehensive job information by joining data from multiple database tables including Jobs, Companies, Locations, and Countries tables.