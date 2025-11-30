# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Matching Service** is a Python FastAPI application that matches job seekers' resumes with relevant job opportunities using semantic vector embeddings and multi-metric similarity ranking. The service combines PostgreSQL (with pgvector), MongoDB, and Redis to provide high-performance, scalable job matching with advanced filtering capabilities.

**Documentation**: Comprehensive documentation is available in the `docs/` directory. See [docs/README.md](docs/README.md) for the full documentation index including ADRs, HLDs, runbooks, and technical guides.

## Technology Stack

- **Framework**: FastAPI 0.115.4 with Uvicorn (async/await throughout)
- **Python**: 3.10-3.12 (managed via Poetry)
- **Databases**:
  - PostgreSQL with pgvector (0.3.6) - 1024-dimensional embeddings with DiskANN indices
  - MongoDB (Motor 3.6.0) - Resume embeddings and user data
  - Redis (5.2.0) - Result caching (TTL: 300s)
- **ML/NLP**: FAISS (1.9.0), LangChain (0.3.7), Spacy (3.8.7), scikit-learn (1.5.2)
- **Connection Pooling**: Psycopg3 (3.2.3) with custom pool manager
- **Testing**: pytest (8.3.3) with pytest-asyncio (0.24.0)

## Development Commands

```bash
# Setup (Poetry is used for dependency management)
pip install -r requirements.txt             # Standard install
poetry install                              # Or use Poetry

# Run application
python app/main.py                          # Default port 8000
uvicorn app.main:app --reload --port 8002  # With auto-reload

# Testing
pytest                                      # Run all tests
pytest -q -x                                # Quick run with fail-fast
pytest --cov=app --cov-report=html         # Generate coverage report
pytest app/tests/test_matcher.py -v        # Run specific test file
pytest app/tests/test_matcher.py::test_function_name -v  # Run single test
pytest -k "keyword"                         # Run tests matching keyword

# Code quality
black --check .                             # Check formatting
ruff check .                                # Lint check
black .                                     # Auto-format
ruff check . --fix                          # Auto-fix lint issues

# Database
alembic upgrade head                        # Apply migrations
alembic revision --autogenerate -m "msg"   # Create migration
python -m app.scripts.init_db              # Initialize database
python -m app.scripts.upgrade_diskann_index # Fix pgvector DiskANN issues

# Docker
docker build -t matching-service .
docker-compose up -d
./run_local.sh                              # Quick local setup
./setup.sh                                  # Full setup with Nginx + SSL

# Health checks
curl http://localhost:8002/health           # Basic health
curl http://localhost:8002/health/db        # Database health
curl http://localhost:8002/health/mongodb   # MongoDB health
```

## Architecture

### Layered Service Architecture

```
API Layer (routers/)
    ↓
Service Layer (services/)
    ↓
Matching Engine (libs/job_matcher/)
    ↓
Data Access (PostgreSQL + MongoDB + Redis)
```

### Core Components

**Job Matching Engine** (`app/libs/job_matcher/`):
- `matcher.py` - Orchestrates the matching process with caching
- `vector_matcher.py` - Coordinates vector similarity search
- `similarity_searcher.py` - Executes PostgreSQL pgvector queries
- `query_builder.py` - Builds SQL with filters (location, keywords, experience)
- `cache.py` - Multi-layer caching (Redis + in-memory LRU)

**Services** (`app/services/`):
- `matching_service.py` - Main business logic for job matching
- `applied_jobs_service.py` - Filters out already-applied jobs
- `cooled_jobs_service.py` - Handles temporarily rejected jobs

**API Routers** (`app/routers/`):
- `jobs_matched_router_async.py` - Main async job matching endpoints
- `healthcheck_router.py` - Health check endpoints
- `rejections_router.py` - Rejection handling
- `cronrouters.py` - Scheduled tasks

**Infrastructure**:
- `app/core/config.py` - Environment-based configuration (50+ settings)
- `app/utils/db_utils.py` - Custom Psycopg connection pooling with health checks
- `app/tasks/job_processor.py` - TaskManager for async background processing
- `app/metrics/` - Comprehensive observability (StatsD/Prometheus backends)

### Vector Similarity Matching

The service uses **1024-dimensional embeddings** stored in PostgreSQL with pgvector:

1. **Similarity Metrics**: Combines L2 distance, cosine similarity, and inner product with weighted scoring (0.4 + 0.4 + 0.2)
2. **Index Types**: Supports both IVFFlat and HNSW indices (configurable via `VECTOR_INDEX_TYPE`)
3. **DiskANN**: Uses PostgreSQL pgvector DiskANN indices for fast approximate nearest neighbor search
4. **Query Flow**:
   - Retrieve resume embedding from MongoDB
   - Build SQL query with filters (QueryBuilder)
   - Execute vector similarity search (SimilaritySearcher)
   - Combine and weight similarity scores
   - Apply applied/cooled jobs filtering
   - Sort by DATE or RECOMMENDED algorithm
   - Cache results in Redis

### Database Strategy

**PostgreSQL** (primary):
- Jobs table with embeddings (pgvector type)
- Normalized tables: Fields, Companies, Locations, Countries
- PostGIS extension for geospatial queries (POINT geometry)
- DiskANN indices for vector similarity search

**MongoDB** (user-specific):
- Resumes collection with embeddings
- Applied jobs history
- Cooled jobs (user rejections)
- Task results storage

**Redis** (caching):
- Matched results cache (TTL: 300s, configurable via `REDIS_CACHE_TTL`)
- Falls back to in-memory cache if Redis unavailable
- Cache key includes all filter parameters

### Authentication

- **JWT tokens**: Validated via `get_current_user()` dependency
- **API keys**: Internal service-to-service auth via `INTERNAL_API_KEY`
- Configured in `app/core/auth.py` and `app/core/security.py`

### Connection Pooling

Custom Psycopg connection pool (`app/utils/db_utils.py`):
- Configurable min/max pool size (`DB_POOL_MIN_SIZE`, `DB_POOL_MAX_SIZE`)
- Statement timeout configurable via `DB_STATEMENT_TIMEOUT` (default: 60000ms)
- Health checks with automatic reconnection
- Supports multiple named pools for different query types

## Key Configuration

Environment variables (see `.env.example`):

**Database**:
- `DATABASE_URL` - PostgreSQL connection string
- `MONGODB` - MongoDB connection string
- `DB_POOL_MIN_SIZE`, `DB_POOL_MAX_SIZE` - Connection pool tuning
- `DB_STATEMENT_TIMEOUT` - Query timeout in milliseconds (default: 60000)

**Redis**:
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD`
- `REDIS_CACHE_TTL` - Cache expiration in seconds (default: 300)
- `REDIS_ENABLED` - Enable/disable Redis caching

**Matching**:
- `RETURNED_JOBS_SIZE` - Max jobs returned per query (default: 25)
- `CACHE_SIZE` - In-memory cache size (default: 1000)
- `DEFAULT_GEO_RADIUS_METERS` - Default location radius (default: 50000)

**Vector Indices**:
- `VECTOR_INDEX_TYPE` - "ivfflat" or "hnsw"
- `VECTOR_IVF_LISTS`, `VECTOR_IVF_PROBES` - IVFFlat tuning
- `VECTOR_HNSW_M`, `VECTOR_HNSW_EF_CONSTRUCTION`, `VECTOR_HNSW_EF_SEARCH` - HNSW tuning

**Authentication**:
- `SECRET_KEY` - JWT signing key
- `ALGORITHM` - JWT algorithm (default: HS256)
- `ACCESS_TOKEN_EXPIRE_MINUTES` - Token expiration (default: 60)
- `INTERNAL_API_KEY` - Service-to-service authentication

**LLM** (for quality evaluation):
- `OPENAI_API_KEY`
- `LLM_BASE_URL` (default: https://openrouter.ai/api/v1)
- `LLM_MODEL_NAME` (default: openai/gpt-4o-mini)

**Metrics**:
- `METRICS_ENABLED`, `METRICS_BACKEND` (statsd/prometheus)
- `METRICS_COLLECTION_ENABLED` - Enable detailed metrics
- `INCLUDE_TIMING_HEADER` - Add X-Process-Time header

## API Endpoints

**Job Matching**:
- `GET /jobs/match` - Get cached matches with optional filters
- `POST /jobs/match` - Trigger new matching (returns task_id)
- `GET /jobs/match/status/{task_id}` - Poll task status

**Query Parameters for GET /jobs/match**:
- `keywords` - List of required keywords
- `country` - Hard filter (excludes all jobs outside country)
- `city` - Soft filter (keeps remote jobs)
- `latitude`, `longitude`, `radius_km` - Geographic circle filter
- `offset` - Pagination (max 2000)
- `experience` - Filter by level (Entry-level, Mid-level, Senior-level, Executive-level, Internship)
- `is_remote_only` - Only remote jobs
- `sort_type` - "DATE" or "RECOMMENDED"

**Health Checks**:
- `GET /health` - Service health
- `GET /health/db` - PostgreSQL connectivity
- `GET /health/mongodb` - MongoDB connectivity

**Quality Tracking** (optional):
- `POST /quality/evaluate` - LLM-based match evaluation
- `POST /quality/feedback` - User feedback submission
- `GET /quality/metrics` - Quality metrics retrieval

## Testing Strategy

- **Coverage**: 33% overall, 80%+ on critical modules (job_matcher, matching_service)
- **Key Test Files**:
  - `app/tests/test_matcher.py` - Core matching logic validation
  - `app/tests/test_matching_service.py` - Service layer tests
  - `app/tests/test_experience_filter.py` - Experience level filtering
  - `app/tests/test_phrase_search.py` - Keyword search validation
- **Async Testing**: Uses pytest-asyncio with `asyncio_default_fixture_loop_scope = function`
- **Mocking**: pytest-mock for external dependencies

## Important Implementation Details

### Async-First Design

All I/O operations use async/await for non-blocking execution. Key patterns:
- Database queries: async with connection pool
- MongoDB operations: Motor async driver
- Redis operations: async redis-py
- Background tasks: asyncio.create_task() via TaskManager

### Task Management System

`TaskManager` class (`app/tasks/job_processor.py`):
- Creates tasks with unique IDs, returns immediately (202 Accepted)
- Executes matching in background
- Stores results in MongoDB and in-memory
- 1-hour task expiration with automatic cleanup
- Supports blocking wait via `wait_for_result()`

### Sorting Algorithms

**DATE Sort**:
- Primary: Job posting date (newest first)
- Secondary: Match score with penalties for low scores

**RECOMMENDED Sort**:
- Exponential decay based on posting date
- Weighted by match score
- Balances recency vs relevance

### Location Filtering

**Hard Filter** (country):
- Excludes ALL jobs outside specified country (including remote)
- Applied at SQL level

**Soft Filter** (city):
- Excludes jobs in different city BUT allows remote jobs
- Uses PostGIS distance calculations with configurable radius

**Radius Search**:
- Requires latitude, longitude, radius_km parameters
- Uses PostGIS ST_DWithin for efficient spatial queries

### Caching Strategy

1. **Check Redis cache** - Distributed cache with TTL
2. **Check in-memory cache** - LRU eviction, per-process
3. **Execute query** - If cache miss
4. **Store in both caches** - For next request

Cache key includes: user_id, filters (country, city, keywords, experience, location params)

### Metrics Collection

**Backends**: StatsD (Datadog) or Prometheus
**Tracked Metrics**:
- Request timing (middleware)
- Algorithm execution time (decorators)
- Database query timing
- System metrics (CPU, memory)
- Slow request detection (>1000ms threshold)

Enable via `METRICS_ENABLED=true` and `METRICS_COLLECTION_ENABLED=true`

### Error Handling

- Comprehensive exception hierarchy in `job_matcher/`
- Graceful degradation when Redis unavailable
- Database query timeouts (1500ms statement timeout)
- Detailed error logging with context via Loguru
- Structured JSON logs (configurable via `JSON_LOGS`)

## Common Issues

### DiskANN Index Upgrade

If you see "diskann index needs to be upgraded to version 2":
```bash
# Quick fix (if vector dimensions unchanged)
python -m app.scripts.upgrade_diskann_index

# Advanced fix with options
python -m app.scripts.fix_diskann_index --mode=upgrade
```

See `app/scripts/README_diskann_fix.md` for details.

### Connection Pool Exhaustion

If experiencing connection issues:
1. Check `DB_POOL_MAX_SIZE` setting (default: 10)
2. Monitor pool usage in logs
3. Increase max_size or reduce query load
4. Check for leaked connections (ensure proper cleanup)

### Cache Inconsistency

If cached results seem stale:
1. Check `REDIS_CACHE_TTL` setting (default: 300s)
2. Manually flush Redis: `redis-cli FLUSHDB`
3. Verify cache key generation in `cache.py`
4. Check Redis connectivity via `/health/redis`

## Development Workflow

Located in `dev-prompts/`:
- **Protocol-based workflows**: `*-PROTO.yaml` files define development lifecycle
- **Multi-agent orchestrator**: Python system in `orchestrator/` directory
- **Standards**: TDD workflow, conventional commits, 95-100% test coverage goal
- **Documentation protocol**: `DOCS-KEEPER-PROTO.yaml` defines documentation standards and maintenance

Note: The `dev-prompts/` folder is a separate project for development workflow automation and should not be confused with the matching service itself.

## Documentation Structure

The project follows the DOCS-KEEPER protocol for comprehensive documentation:

**Root Level**:
- `README.md` - Project overview for external users
- `CLAUDE.md` - This file, primary guide for Claude Code and developers
- `CHANGELOG.md` - Version history following Keep a Changelog format

**docs/ Directory**:
- `docs/README.md` - Master documentation index
- `docs/adr/` - Architecture Decision Records (immutable once accepted)
- `docs/hld/` - High-Level Designs for complex features
- `docs/delivery-plan/` - Delivery planning documents
- `docs/investigations/` - Bug investigation documentation
- `docs/fixes/` - Bug fix documentation
- `docs/issues/` - Known issues and workarounds
- `docs/root-cause-analysis/` - RCA documents for major incidents
- `docs/runbooks/` - Operational procedures for alerts and incidents

For detailed documentation guidelines, see [docs/README.md](docs/README.md).

## File References

When working with code, use this format for references:
- `app/libs/job_matcher/matcher.py:150` - Job matching cache check logic
- `app/services/matching_service.py:75` - Resume retrieval from MongoDB
- `app/utils/db_utils.py:45` - Connection pool initialization
- `app/core/config.py:92` - Metrics settings configuration
