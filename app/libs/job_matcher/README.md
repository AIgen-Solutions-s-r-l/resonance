# Job Matcher Module Structure

This document outlines the restructured job matcher module organization with a focus on separation of concerns and SOLID principles.

## Files and Responsibilities

### Core Components

- **`models.py`** - Data models for job matching
- **`exceptions.py`** - Custom exception hierarchy
- **`job_validator.py`** - Validates job data and constructs JobMatch objects
- **`vector_matcher.py`** - Coordinates vector similarity matching
- **`similarity_searcher.py`** - Executes database queries for similarity search
- **`matcher.py`** - Primary entry point for job matching operations
- **`cache.py`** - Caching mechanism for job matching results
- **`query_builder.py`** - SQL query construction
- **`persistence.py`** - Handles saving results
- **`utils.py`** - Helper utilities for logging and performance tracking

## Key Structural Improvements

### 1. Clear Separation of Concerns

- **Data Validation (job_validator.py)**: Focused solely on validating job data and constructing JobMatch objects
- **Query Construction (query_builder.py)**: Builds SQL queries with proper filtering
- **Query Execution (similarity_searcher.py)**: Executes the actual database operations
- **Vector Matching (vector_matcher.py)**: Coordinates the similarity search process

### 2. Better Component Organization

Previous structure used generic names like `matcher_vector.py` and `matcher_vector_part2.py` that didn't clearly express purpose. The new structure uses meaningful component names that reflect their responsibilities.

### 3. Improved Logging and Metrics

Each component contains detailed performance logging:
- Execution times for all operations
- Entry/exit logging
- Detailed context for debugging

### 4. Component Flow

1. `JobMatcher` (in matcher.py) receives match requests
2. Checks cache via `cache.py`
3. If not cached, delegates to `vector_matcher.py`
4. `VectorMatcher` coordinates the query building and execution
5. `query_builder.py` constructs the SQL conditions
6. `similarity_searcher.py` executes the database queries
7. `job_validator.py` validates and constructs JobMatch objects
8. Results stored in cache and returned

## Error Handling

- Clear exception hierarchy in `exceptions.py`
- Each component handles its domain-specific errors
- Detailed logging of error contexts

## Performance Monitoring

- Execution time tracking in all components
- Clear metrics boundaries
- Query performance logging