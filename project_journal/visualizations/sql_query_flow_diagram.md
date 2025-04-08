# SQL Query Flow Diagram

This diagram illustrates the flow of SQL queries in the matching service project, showing how job matching requests are processed from API endpoints to database queries, with an emphasis on geolocation prioritization and the streamlined query path.

```mermaid
flowchart TD
    %% Main components
    API[API Endpoints<br/>app/routers/jobs_matched_router_async.py]
    MS[Matching Service<br/>app/services/matching_service.py]
    OJM[OptimizedJobMatcher<br/>app/libs/job_matcher/__init__.py]
    JM[JobMatcher<br/>app/libs/job_matcher/matcher.py]
    QB[Query Builder<br/>app/libs/job_matcher/query_builder.py]
    VM[Vector Matcher<br/>app/libs/job_matcher/vector_matcher.py]
    Cache[Cache<br/>app/libs/job_matcher/cache.py]
    Persist[Persistence<br/>app/libs/job_matcher/persistence.py]
    SS[Similarity Searcher<br/>app/libs/job_matcher/similarity_searcher.py]
    JV[Job Validator<br/>app/libs/job_matcher/job_validator.py]
    DBUtils[DB Utils<br/>app/utils/db_utils.py]
    DB[(PostgreSQL<br/>Database)]

    %% Connections
    API -->|"Request for job matching"| MS
    MS -->|"Calls match_jobs_with_resume()"| OJM
    OJM -->|"Delegates to"| JM
    
    %% JobMatcher connections
    JM -->|"Builds filter conditions"| QB
    JM -->|"Finds matching jobs"| VM
    JM -->|"Caches results"| Cache
    JM -->|"Saves results"| Persist
    
    %% Vector Matcher connections
    VM -->|"Executes similarity queries"| SS
    VM -->|"Builds filter conditions"| QB
    
    %% Similarity Searcher connections
    SS -->|"Executes vector queries"| DBUtils
    SS -->|"Validates job matches"| JV
    
    %% DB Utils connections
    DBUtils -->|"Connection pooling<br/>SQL execution<br/>Vector similarity ops"| DB
    
    %% SQL Query Flow subgraph with detailed query paths
    subgraph "SQL Query Flow"
        direction TB
        step1[Step 1: Build filter conditions]
        geoStep[Step 1a: Geolocation Filter<br/>Prioritize lat/long coordinates<br/>Disregard city when lat/long provided]
        otherFilters[Step 1b: Other Filters<br/>keywords, experience, etc.]
        
        %% Full Count Query (when needed for pagination)
        fullCount[Full Count Query<br/>get_filtered_job_count with fast=False<br/>Complete COUNT for pagination]
        
        %% Vector Query - now always used
        vectorQuery[Vector Similarity Query<br/>_execute_vector_query<br/>Always uses vector similarity with embedding]
        
        %% Final steps
        step3[Step 3: Filter out already applied jobs]
        step4[Step 4: Cache results for future requests]
        
        %% Flow connections
        step1 --> geoStep
        step1 --> otherFilters
        geoStep --> vectorQuery
        otherFilters --> vectorQuery
        
        %% Connect to pagination when needed
        vectorQuery -->|"If pagination needed"| fullCount
        
        %% Continue flow
        vectorQuery --> step3
        fullCount --> step3
        step3 --> step4
    end
    
    %% Connect SQL Flow to components
    QB -.-> step1
    QB -.-> geoStep
    QB -.-> otherFilters
    DBUtils -.-> fullCount
    SS -.-> vectorQuery
    JM -.-> step3
    Cache -.-> step4
    
    %% Styling
    classDef apiClass fill:#f9f,stroke:#333,stroke-width:2px;
    classDef serviceClass fill:#bbf,stroke:#333,stroke-width:1px;
    classDef matcherClass fill:#bfb,stroke:#333,stroke-width:1px;
    classDef utilClass fill:#fbb,stroke:#333,stroke-width:1px;
    classDef dbClass fill:#bbb,stroke:#333,stroke-width:2px;
    classDef flowClass fill:#fffacd,stroke:#333,stroke-width:1px;
    classDef geoClass fill:#e6f7ff,stroke:#333,stroke-width:1px; %% For geo step styling
    classDef queryClass fill:#98fb98,stroke:#333,stroke-width:1px;
    
    class API apiClass;
    class MS,OJM,JM,VM,QB,Cache,Persist,SS,JV serviceClass;
    class DBUtils utilClass;
    class DB dbClass;
    class step1,step3,step4,otherFilters flowClass;
    class geoStep geoClass;
    class fullCount,vectorQuery queryClass;
```

The diagram shows the following components and flows:

**Request Flow**: Starting from API endpoints, requests flow through the matching service to the job matcher components.

**Component Interactions**: How different components interact with each other:
JobMatcher uses QueryBuilder, VectorMatcher, Cache, and Persistence;
VectorMatcher uses SimilaritySearcher and QueryBuilder;
SimilaritySearcher uses DB Utils and JobValidator.

**SQL Query Flow**: The detailed query process including:
Building filter conditions with prioritized geolocation handling - Latitude and longitude coordinates are prioritized over city names; When latitude and longitude parameters are provided, city parameters are completely disregarded in the WHERE clause.
Vector Similarity Query: Always used for all job matching queries (in app/libs/job_matcher/similarity_searcher.py, _execute_vector_query method).
Full Count Query: Used when pagination requires total count (in app/utils/db_utils.py, get_filtered_job_count with fast=False).
Filtering out already applied jobs.
Caching results for future requests.

**Database Operations**: How DB Utils handles connection pooling, SQL execution, and vector similarity operations with the PostgreSQL database.

**Streamlined Query Path**:
The system now always uses vector similarity operations for all queries;
The previous optimization that used simpler queries for small result sets has been removed;
This simplifies the query flow while ensuring consistent results across all query sizes.