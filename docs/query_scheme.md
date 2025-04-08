# SQL Query Flow Diagram

This diagram illustrates the flow of SQL queries in the matching service project, showing how job matching requests are processed from API endpoints to database queries, including the different query paths based on result count.

```mermaid
flowchart TD
    %% Main components
    API[API Endpoints\napp/routers/jobs_matched_router_async.py]
    MS[Matching Service\napp/services/matching_service.py]
    OJM[OptimizedJobMatcher\napp/libs/job_matcher/__init__.py]
    JM[JobMatcher\napp/libs/job_matcher/matcher.py]
    QB[Query Builder\napp/libs/job_matcher/query_builder.py]
    VM[Vector Matcher\napp/libs/job_matcher/vector_matcher.py]
    Cache[Cache\napp/libs/job_matcher/cache.py]
    Persist[Persistence\napp/libs/job_matcher/persistence.py]
    SS[Similarity Searcher\napp/libs/job_matcher/similarity_searcher.py]
    JV[Job Validator\napp/libs/job_matcher/job_validator.py]
    DBUtils[DB Utils\napp/utils/db_utils.py]
    DB[(PostgreSQL\nDatabase)]

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
    DBUtils -->|"1. Connection pooling\n2. SQL execution\n3. Vector similarity ops"| DB
    
    %% SQL Query Flow subgraph with detailed query paths
    subgraph "SQL Query Flow"
        direction TB
        step1[1. Build filter conditions\n(location, keywords, experience)]
        
        %% Fast Count Query
        fastCount[Fast Count Query\nget_filtered_job_count(fast=True)\nWITH clause + LIMIT 6]
        
        %% Decision based on Fast Count
        countDecision{Count ≤ 5?}
        
        %% Query paths
        fallbackQuery[Fallback Query\n_execute_fallback_query()\nSimpler query without vector ops]
        vectorQuery[Vector Similarity Query\n_execute_vector_query()\nUses vector similarity with embedding <=> operator]
        
        %% Full Count Query (when needed for pagination)
        fullCount[Full Count Query\nget_filtered_job_count(fast=False)\nComplete COUNT(*) without LIMIT]
        
        %% Final steps
        step3[3. Filter out already applied jobs]
        step4[4. Cache results for future requests]
        
        %% Flow connections
        step1 --> fastCount
        fastCount --> countDecision
        countDecision -->|"Yes (≤ 5 jobs)"| fallbackQuery
        countDecision -->|"No (> 5 jobs)"| vectorQuery
        
        %% Connect to pagination when needed
        countDecision -->|"If pagination needed"| fullCount
        
        %% Merge paths back
        fallbackQuery --> step3
        vectorQuery --> step3
        step3 --> step4
    end
    
    %% Connect SQL Flow to components
    QB -.-> step1
    DBUtils -.-> fastCount
    DBUtils -.-> fullCount
    SS -.-> fallbackQuery
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
    classDef decisionClass fill:#ffd700,stroke:#333,stroke-width:1px;
    classDef queryClass fill:#98fb98,stroke:#333,stroke-width:1px;
    
    class API apiClass;
    class MS,OJM,JM,VM,QB,Cache,Persist,SS,JV serviceClass;
    class DBUtils utilClass;
    class DB dbClass;
    class step1,step3,step4 flowClass;
    class countDecision decisionClass;
    class fastCount,fullCount,fallbackQuery,vectorQuery queryClass;
```

The diagram shows:

1. **Request Flow**: Starting from API endpoints, requests flow through the matching service to the job matcher components.

2. **Component Interactions**: How different components interact with each other:
   - JobMatcher uses QueryBuilder, VectorMatcher, Cache, and Persistence
   - VectorMatcher uses SimilaritySearcher and QueryBuilder
   - SimilaritySearcher uses DB Utils and JobValidator

3. **SQL Query Flow**: The detailed query process including:
   - Building filter conditions
   - **Fast Count Query**: Quick check if there are more than 5 matching jobs (in `app/utils/db_utils.py`, `get_filtered_job_count` with `fast=True`)
   - Decision point based on count results:
     - If count ≤ 5: Use **Fallback Query** (in `app/libs/job_matcher/similarity_searcher.py`, `_execute_fallback_query` method)
     - If count > 5: Use **Vector Similarity Query** (in `app/libs/job_matcher/similarity_searcher.py`, `_execute_vector_query` method)
   - **Full Count Query**: Used when pagination requires total count (in `app/utils/db_utils.py`, `get_filtered_job_count` with `fast=False`)
   - Filtering out already applied jobs
   - Caching results for future requests

4. **Database Operations**: How DB Utils handles connection pooling, SQL execution, and vector similarity operations with the PostgreSQL database.

5. **Query Optimization Paths**:
   - The system optimizes query execution by using simpler queries for small result sets
   - More complex vector similarity operations are only used when necessary for larger result sets