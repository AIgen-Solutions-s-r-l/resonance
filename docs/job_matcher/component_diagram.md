# Job Matcher Component Diagrams

This document provides visual representations of the Job Matcher module's architecture and component interactions.

## High-Level Architecture

```mermaid
graph TD
    Client[Client Application] --> API[API Layer]
    API --> JobMatcher[Job Matcher]
    JobMatcher --> Cache[Cache]
    JobMatcher --> VectorMatcher[Vector Matcher]
    JobMatcher --> Persistence[Persistence]
    VectorMatcher --> QueryBuilder[Query Builder]
    VectorMatcher --> SimilaritySearcher[Similarity Searcher]
    SimilaritySearcher --> JobValidator[Job Validator]
    SimilaritySearcher --> Database[(PostgreSQL Database)]
    Persistence --> MongoDB[(MongoDB)]
    
    style Client fill:#f9f,stroke:#333,stroke-width:2px
    style API fill:#f9f,stroke:#333,stroke-width:2px
    style JobMatcher fill:#bbf,stroke:#333,stroke-width:2px
    style Cache fill:#bbf,stroke:#333,stroke-width:2px
    style VectorMatcher fill:#bbf,stroke:#333,stroke-width:2px
    style QueryBuilder fill:#bbf,stroke:#333,stroke-width:2px
    style SimilaritySearcher fill:#bbf,stroke:#333,stroke-width:2px
    style JobValidator fill:#bbf,stroke:#333,stroke-width:2px
    style Persistence fill:#bbf,stroke:#333,stroke-width:2px
    style Database fill:#dfd,stroke:#333,stroke-width:2px
    style MongoDB fill:#dfd,stroke:#333,stroke-width:2px
```

## Component Relationships

```mermaid
classDiagram
    class JobMatcher {
        +process_job()
    }
    
    class Cache {
        +get()
        +set()
        +generate_key()
    }
    
    class VectorMatcher {
        +get_top_jobs()
    }
    
    class QueryBuilder {
        +build_filter_conditions()
        -_build_location_filters()
        -_build_keyword_filters()
    }
    
    class SimilaritySearcher {
        +_execute_vector_query()
        +_execute_fallback_query()
    }
    
    class JobValidator {
        +create_job_match()
        +validate_row_data()
    }
    
    class Persistence {
        +save_matches()
    }
    
    class JobMatch {
        +id
        +title
        +description
        +score
        +to_dict()
    }
    
    JobMatcher --> Cache : uses
    JobMatcher --> VectorMatcher : uses
    JobMatcher --> Persistence : uses
    VectorMatcher --> QueryBuilder : uses
    VectorMatcher --> SimilaritySearcher : uses
    SimilaritySearcher --> JobValidator : uses
    JobValidator --> JobMatch : creates
```

## Data Flow Diagram

```mermaid
sequenceDiagram
    participant Client
    participant JobMatcher
    participant Cache
    participant VectorMatcher
    participant QueryBuilder
    participant SimilaritySearcher
    participant Database
    participant JobValidator
    participant Persistence
    
    Client->>JobMatcher: process_job(resume, location, keywords)
    JobMatcher->>Cache: check cache
    
    alt Cache Hit
        Cache-->>JobMatcher: return cached results
    else Cache Miss
        JobMatcher->>VectorMatcher: get_top_jobs
        VectorMatcher->>QueryBuilder: build_filter_conditions
        QueryBuilder-->>VectorMatcher: where_clauses, query_params
        
        VectorMatcher->>Database: get_filtered_job_count
        Database-->>VectorMatcher: row_count
        
        alt Small Result Set
            VectorMatcher->>SimilaritySearcher: execute_fallback_query
            SimilaritySearcher->>Database: execute simple query
        else Normal Result Set
            VectorMatcher->>SimilaritySearcher: execute_vector_query
            SimilaritySearcher->>Database: execute vector similarity query
        end
        
        Database-->>SimilaritySearcher: raw results
        SimilaritySearcher->>JobValidator: create_job_match for each row
        JobValidator-->>SimilaritySearcher: validated job matches
        SimilaritySearcher-->>VectorMatcher: job matches
        VectorMatcher-->>JobMatcher: job matches
        
        JobMatcher->>Cache: store results
        
        alt Save to MongoDB
            JobMatcher->>Persistence: save_matches
            Persistence->>Database: store in MongoDB
        end
    end
    
    JobMatcher-->>Client: return job matches
```

## Vector Similarity Process

```mermaid
graph LR
    A[Resume Vector] --> B{Pre-filtering}
    B -->|Location Filter| C[Filtered Job Set]
    B -->|Keyword Filter| C
    C --> D[Vector Similarity Calculation]
    D --> E[Sort by Similarity Score]
    E --> F[Top K Results]
    F --> G[Validate & Transform]
    G --> H[Final Job Matches]
    
    style A fill:#f9f,stroke:#333,stroke-width:2px
    style B fill:#bbf,stroke:#333,stroke-width:2px
    style C fill:#bbf,stroke:#333,stroke-width:2px
    style D fill:#bbf,stroke:#333,stroke-width:2px
    style E fill:#bbf,stroke:#333,stroke-width:2px
    style F fill:#bbf,stroke:#333,stroke-width:2px
    style G fill:#bbf,stroke:#333,stroke-width:2px
    style H fill:#bbf,stroke:#333,stroke-width:2px
```

## Caching Mechanism

```mermaid
graph TD
    A[Request] --> B{Cache Check}
    B -->|Cache Hit| C[Return Cached Results]
    B -->|Cache Miss| D[Process Request]
    D --> E[Store in Cache]
    E --> F[Return Results]
    C --> F
    
    G[Cache Size Check] --> H{Size > Max?}
    H -->|Yes| I[Remove Oldest Entries]
    H -->|No| J[Do Nothing]
    I --> J
    
    style A fill:#f9f,stroke:#333,stroke-width:2px
    style B fill:#bbf,stroke:#333,stroke-width:2px
    style C fill:#bbf,stroke:#333,stroke-width:2px
    style D fill:#bbf,stroke:#333,stroke-width:2px
    style E fill:#bbf,stroke:#333,stroke-width:2px
    style F fill:#bbf,stroke:#333,stroke-width:2px
    style G fill:#dfd,stroke:#333,stroke-width:2px
    style H fill:#dfd,stroke:#333,stroke-width:2px
    style I fill:#dfd,stroke:#333,stroke-width:2px
    style J fill:#dfd,stroke:#333,stroke-width:2px
```

## Error Handling Flow

```mermaid
graph TD
    A[Operation] --> B{Error?}
    B -->|Yes| C[Log Error]
    B -->|No| D[Continue Processing]
    C --> E{Recoverable?}
    E -->|Yes| F[Apply Recovery Strategy]
    E -->|No| G[Raise Exception]
    F --> D
    
    style A fill:#f9f,stroke:#333,stroke-width:2px
    style B fill:#bbf,stroke:#333,stroke-width:2px
    style C fill:#bbf,stroke:#333,stroke-width:2px
    style D fill:#bbf,stroke:#333,stroke-width:2px
    style E fill:#bbf,stroke:#333,stroke-width:2px
    style F fill:#bbf,stroke:#333,stroke-width:2px
    style G fill:#faa,stroke:#333,stroke-width:2px