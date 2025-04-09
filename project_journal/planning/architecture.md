# Matching Service Architecture

## System Overview

The Matching Service is a sophisticated system designed to match job seekers with relevant job opportunities using vector similarity search. The system processes resume data and returns a list of matching jobs based on vector similarity, location preferences, keywords, and other filtering criteria.

## Core Components

### 1. API Layer

The API layer provides RESTful endpoints for clients to interact with the matching service:

- **JobsMatchedRouter**: Handles job matching requests
  - `GET /jobs/matched`: Get matched jobs for a user
  - `POST /jobs/match`: Match jobs with a provided resume

- **HealthcheckRouter**: Provides health check endpoints
  - `GET /health`: Overall service health
  - `GET /health/db`: Database health
  - `GET /health/mongodb`: MongoDB health

### 2. Services Layer

The services layer contains business logic for the application:

- **MatchingService**: Coordinates the job matching process
  - `get_resume_by_user_id()`: Retrieves a user's resume from MongoDB
  - `match_jobs_with_resume()`: Matches jobs with a resume

- **AppliedJobsService**: Handles filtering of already applied jobs
  - `get_applied_jobs()`: Retrieves jobs a user has already applied for
  - `is_job_applied()`: Checks if a user has applied for a specific job

- **CooledJobsService**: Handles filtering of cooled jobs
  - `get_cooled_jobs()`: Retrieves jobs that are in the cooling period

### 3. Job Matcher Module

The Job Matcher module is the core of the matching functionality:

- **JobMatcher**: Primary entry point for job matching operations
  - Orchestrates the entire matching process
  - Handles caching and result persistence

- **VectorMatcher**: Coordinates vector similarity matching
  - Decides between optimized vector search and fallback strategies
  - Handles performance monitoring and error reporting

- **QueryBuilder**: Constructs SQL queries with proper filtering
  - Handles location and keyword-based filtering
  - Optimizes query structure for performance

- **SimilaritySearcher**: Executes database queries for similarity search
  - Implements vector similarity algorithms
  - Provides fallback mechanisms for edge cases

- **Cache**: Provides caching functionality for job matching results
  - Implements TTL-based expiration and size-based cleanup
  - Thread-safe with async locking mechanism

- **Persistence**: Handles saving results to various storage systems
  - Supports MongoDB persistence
  - Provides error handling and logging

### 4. Database Layer

The system uses two primary databases:

- **PostgreSQL**: Stores job data with vector embeddings
  - Jobs Table: Contains job details and vector embeddings
  - Companies Table: Contains company information
  - Locations Table: Contains location information

- **MongoDB**: Stores resume data and matching results
  - Resumes Collection: Contains user resumes with vector embeddings
  - Job Matches Collection: Contains saved job matches
  - Already Applied Jobs Collection: Contains jobs users have already applied for
  - Cooled Jobs Collection: Contains jobs that are in the cooling period

## Data Flow

### Job Matching Process

1. Client sends a job matching request with a user ID or resume data
2. MatchingService retrieves the user's resume from MongoDB (if user ID provided)
3. MatchingService calls JobMatcher to process the job matching
4. JobMatcher checks the cache for existing results
5. If cache hit, JobMatcher returns cached results
6. If cache miss:
   - JobMatcher fetches applied job IDs from AppliedJobsService
   - JobMatcher fetches cooled job IDs from CooledJobsService
   - JobMatcher calls VectorMatcher to perform vector similarity search
   - VectorMatcher builds filter conditions using QueryBuilder
   - VectorMatcher calls SimilaritySearcher to execute the database query
   - SimilaritySearcher returns job matches
   - JobMatcher stores results in cache
   - JobMatcher saves results to MongoDB (if requested)
7. MatchingService returns job matches to the client

## Database Schema

### PostgreSQL

#### Jobs Table
- `id`: Integer (Primary Key)
- `title`: String
- `description`: Text
- `workplace_type`: String
- `short_description`: String
- `field`: String
- `experience`: String
- `skills_required`: String
- `posted_date`: DateTime
- `job_state`: String
- `apply_link`: String
- `company_id`: Integer (Foreign Key)
- `location_id`: Integer (Foreign Key)
- `embedding`: Vector (1024 dimensions)

#### Companies Table
- `company_id`: Integer (Primary Key)
- `company_name`: String
- `logo`: String

#### Locations Table
- `location_id`: Integer (Primary Key)
- `city`: String
- `country`: Integer (Foreign Key)

### MongoDB

#### Resumes Collection
- `_id`: ObjectId
- `user_id`: Integer
- `version`: String
- `vector`: Array<float>
- `content`: Object

#### Job Matches Collection
- `_id`: ObjectId
- `resume_id`: String
- `timestamp`: DateTime
- `jobs`: Array<Object>

#### Already Applied Jobs Collection
- `_id`: ObjectId
- `user_id`: Integer
- `job_ids`: Array<String>

#### Cooled Jobs Collection
- `_id`: ObjectId
- `job_id`: String
- `timestamp`: DateTime

## Key Features

### 1. Vector Similarity-Based Job Matching

The system uses vector embeddings to represent resumes and jobs, allowing for semantic matching beyond simple keyword matching. The vector similarity search is implemented using PostgreSQL's vector operations.

### 2. Filtering Mechanisms

#### Location Filtering
The system supports filtering jobs by location, including city, country, and radius-based geospatial filtering.

#### Keyword Filtering
Users can provide keywords to further filter job matches based on specific terms.

#### Experience Level Filtering
Jobs can be filtered by experience level (Intern, Entry, Mid, Executive).

#### Applied Jobs Filtering
Jobs that a user has already applied for are filtered out from the matching results. This is implemented at the database query level for efficiency.

#### Cooled Jobs Filtering
Jobs that are in the "cooling period" (stored in the cooled_jobs collection) are filtered out from the matching results. This is also implemented at the database query level.

### 3. Performance Optimizations

#### Caching
The system implements a TTL-based cache with size management to improve performance for repeated queries.

#### Connection Pooling
Database connections are pooled to reduce the overhead of establishing new connections for each query.

#### Query Optimization
- Pre-filtering: Apply filters before vector similarity calculation
- Indexed Vector Operations: Utilize database vector indices
- Result Limiting: Limit the number of results to improve performance

#### Adaptive Query Strategy
The system chooses between vector similarity and simple queries based on the expected result set size.

## Recent Architectural Changes

### Cooled Jobs Filtering (2025-04-09)

A new feature was added to filter out jobs from the "cooled_jobs" MongoDB collection during the matching process. This ensures that jobs in the cooling period are not shown in the matching results.

#### Implementation Details

1. Created a new `CooledJobsService` class in `app/services/cooled_jobs_service.py` that retrieves job IDs from the "cooled_jobs" collection.

2. Modified the `JobMatcher.process_job` method to fetch cooled job IDs and combine them with applied job IDs before passing them to the vector matcher.

3. Updated the cache key generation to include cooled job IDs to ensure that changes in the "cooled_jobs" collection invalidate the relevant cache entries.

#### Architecture Decision

The decision to create a separate `CooledJobsService` (rather than extending `AppliedJobsService` or creating a comprehensive `JobFilteringService`) was made to maintain a clean separation of concerns while minimizing changes to the existing codebase. This approach follows the established pattern of the existing `AppliedJobsService`.

For more details, see the [Architecture Decision Record](../decisions/20250409-cooled-jobs-filtering.md).

## Future Considerations

### 1. Comprehensive Job Filtering Service

Consider creating a more comprehensive `JobFilteringService` that handles all job filtering (applied jobs, cooled jobs, etc.) to reduce duplication and provide a more unified approach to job filtering.

### 2. Enhanced Caching Strategy

Implement a more sophisticated caching strategy that can handle partial invalidation when only certain filtering criteria change.

### 3. Metrics and Monitoring

Add more detailed metrics to track the performance impact of various filtering mechanisms and identify optimization opportunities.

### 4. Configurable Filtering

Make filtering mechanisms more configurable, allowing for time-based filtering (e.g., don't show jobs applied for in the last 30 days) or user-controlled filtering options.