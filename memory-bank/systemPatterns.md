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

## Code Organization Patterns

### Feature-Based Organization
- Core functionality is organized by feature (jobs, quality tracking, health checks)
- Each feature has its own router, service, and associated models

### Core Modules Separation
- Core infrastructure concerns separated in `app/core/` 
- Authentication, configuration, database connections kept separate from business logic

## Data Access Patterns

### Multiple Database Strategy
- PostgreSQL used for relational data and structured information
  - Stores job descriptions, company information, locations
  - Utilizes vector embeddings for similarity matching
- MongoDB used for document storage and flexible schema data
  - Stores resume information with vector embeddings
  - Maintains job match results
- Abstracted database access through repository pattern

### Repository Pattern
- Data access logic encapsulated in repository classes
- Business logic interacts with data through repository interfaces
- Example: QualityTrackingRepository separates data access from service logic

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

## Future Pattern Considerations

### Caching Strategy
- Consider implementing caching for frequently accessed data
- Explore Redis or in-memory caching options

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