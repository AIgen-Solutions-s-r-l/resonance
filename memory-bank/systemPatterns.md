# System Patterns: Matching Service

This document outlines the architectural patterns, code organization approaches, and development conventions used in the Matching Service.

## Application Architecture Patterns

### Service-Oriented Design
- The application is organized around core services that handle specific business domains
- Services are kept loosely coupled to allow for independent development and scaling
- Key services: MatchingService, QualityEvaluationService, MetricsTrackingService

### Layer-Based Architecture
- **API Layer**: FastAPI routers in `app/routers/`
- **Service Layer**: Business logic in `app/services/`
- **Repository Layer**: Data access in `app/repositories/`
- **Domain Layer**: Models in `app/models/` and schemas in `app/schemas/`

### Module-Based Organization
- Core functionality refactored into modular components following SOLID principles
- Each component has a clear single responsibility
- Clear separation of concerns between data validation, query building, and execution
- Example: Job matcher module in `app/libs/job_matcher/` with specialized components

## Code Organization Patterns

### Feature-Based Organization
- Core functionality is organized by feature (jobs, quality tracking, health checks)
- Each feature has its own router, service, and associated models

### Core Modules Separation
- Core infrastructure concerns separated in `app/core/` 
- Authentication, configuration, database connections kept separate from business logic

### SOLID Principles Implementation
- **Single Responsibility**: Each module file has exactly one reason to change
  - Example: `query_builder.py` handles only SQL query construction
  - Example: `job_validator.py` focuses exclusively on data validation
- **Open-Closed**: Components designed for extension without modification
  - Example: Custom exception hierarchy allows adding new error types
- **Interface Segregation**: Focused interfaces for specific use cases
  - Example: Separation between vector matcher and persistence services

## Design Patterns

### Singleton Pattern
- Used for components that should have only one instance
- Examples: query_builder, job_validator, vector_matcher
- Ensures consistent state and reduces memory overhead

### Factory Pattern
- Used for object creation with complex validation logic
- Example: JobMatch creation in job_validator component
- Centralizes creation logic and validation rules

### Repository Pattern
- Data access logic encapsulated in repository classes
- Business logic interacts with data through repository interfaces
- Example: QualityTrackingRepository separates data access from service logic

### Decorator Pattern
- Used for cross-cutting concerns like metrics and logging
- Example: Performance timing decorators in metrics module
- Example: Async method timing in database operations

### Strategy Pattern
- Different algorithms or approaches can be selected at runtime
- Example: Fallback query strategy when result count is small
- Example: Different similarity metrics combined with weighting

## Data Access Patterns

### Multiple Database Strategy
- PostgreSQL used for relational data and structured information
  - Stores job descriptions, company information, locations
  - Utilizes vector embeddings for similarity matching
- MongoDB used for document storage and flexible schema data
  - Stores resume information with vector embeddings
  - Maintains job match results
- Abstracted database access through repository pattern

### Connection Pooling
- Optimized database access through connection pools
- Reuses database connections to avoid overhead of establishing new connections
- Implements proper async context managers for resource management

### Caching Strategy
- In-memory caching implemented for frequently accessed match results
- TTL-based expiration to ensure data freshness (5-minute default)
- Size-based pruning to prevent memory issues
- Cache key generation based on all query parameters
- Thread-safe implementation with asyncio.Lock()

## Error Handling Patterns

### Custom Exception Hierarchy
- Domain-specific exceptions that extend base Exception class
- Categorized by error type and source component
- Examples: QueryBuildingError, VectorSimilarityError, ValidationError
- Clear error messages with context information

### Graceful Degradation
- Fallback mechanisms when optimal approach fails
- Example: Simplified query execution for small result sets
- Example: Default values when optional parameters are missing

### Comprehensive Logging
- Structured logging with context information
- Separate log files for different concerns:
  - General application logs
  - Error-specific logs with context
  - Performance-focused logs with timing data
- Log rotation and retention policies

## API Design Patterns

### Resource-Oriented Endpoints
- API endpoints organized around resources (/jobs, /health)
- HTTP methods used appropriately (GET for retrieval, POST for actions)
- Query parameters used for filtering (keywords, location, etc.)

### Health Check Pattern
- Dedicated health check endpoints for different system components
- Granular health status for database, MongoDB, and overall system

## Testing Patterns

### Unit Testing
- Individual components tested in isolation
- Mocking used for external dependencies

### Component Testing
- Testing service-level functionality (matcher, matching service)
- Validating business logic without external dependencies

## Data Processing Patterns

### Vector Embedding Approach
- Text content (resumes, job descriptions) converted to vector embeddings
- Embeddings stored in database for efficient similarity calculations
- Enables semantic matching beyond simple keyword matching

### Multi-Metric Similarity Matching
- Multiple similarity metrics used to compare resume and job embeddings:
  - L2 distance (Euclidean distance between vectors)
  - Cosine similarity (angle between vectors)
  - Inner product (dot product of vectors)
- Weighted combination of metrics (0.4, 0.4, 0.2) for final score
- Normalization applied to ensure fair comparison across metrics

### Filtering Pipeline
- Location filtering (country, city)
- Geospatial filtering (radius search using PostgreSQL's ST_DWithin)
- Keyword filtering in job title and description
- Combined SQL query with dynamic WHERE clauses

### Matching and Ranking Pipeline
- Multi-stage processing of resume-job matching
- Ranking algorithms based on multiple metrics
- Results stored and cached for efficient retrieval
- Fallback to simpler queries for small result sets

### Result Persistence
- Results saved to both JSON files and MongoDB
- Timestamp information for tracking match history
- Supports retrieval of previously generated matches

## Performance Optimization Patterns

### Query Optimization
- Use of optimized vector similarity operations
- Efficient parameter handling in SQL queries
- Early filtering to reduce dataset size before computing similarity

### Metrics Collection
- Detailed timing metrics for various operations
- Score distribution analysis for match quality
- Match count tracking by algorithm path
- Response time measurement at API level

### Asynchronous Processing
- Fully asynchronous implementation with proper async/await patterns
- Non-blocking database operations with async cursor
- Concurrent processing where possible

## Future Pattern Considerations

### Distributed Caching
- Consider replacing in-memory cache with Redis for multi-instance deployments
- Implement cache invalidation mechanisms when data changes
- Explore variable TTL based on query popularity

### Asynchronous Processing
- Consider moving intensive matching operations to background tasks
- Implement job queue for processing resume-job matches

### Enhanced Filtering Capabilities
- Expand filtering options beyond current implementation
- Consider adding support for skill-specific matching weights

### Improved Similarity Metrics
- Explore additional similarity metrics beyond the current three
- Consider machine learning approaches for improved matching
- Implement A/B testing framework to evaluate different weighting schemes