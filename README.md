# Matching Service

The **Matching Service** is a Python-based application that matches resumes with job descriptions using advanced metrics and ranking algorithms. It utilizes vector embeddings for semantic matching and employs multiple similarity metrics for precise ranking. The service integrates with PostgreSQL and MongoDB databases and provides RESTful APIs for seamless interaction.

## Table of Contents

- [Overview](#overview)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Architecture](#architecture)
- [Application Workflow](#application-workflow)
- [API Endpoints](#api-endpoints)
- [Running the Application](#running-the-application)
- [Testing](#testing)
- [Folder Structure](#folder-structure)
- [Quality Tracking](#quality-tracking)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

The Matching Service facilitates the matching of resumes to job descriptions by:

1. **Semantic Matching**: Using vector embeddings to understand the meaning beyond keywords.
2. **Multi-Metric Ranking**: Applying multiple similarity metrics (L2 distance, cosine similarity, inner product) with weighted scoring to rank job descriptions.
3. **Flexible Filtering**: Supporting location-based, keyword-based, and radius-based filtering.
4. **Quality Evaluation**: Assessing match quality through automated evaluation and manual feedback.
5. **Providing APIs**: For triggering matching processes, retrieving job matches, and accessing system health.

---

## Requirements

- Python 3.12.7
- MongoDB server
- PostgreSQL database with PostGIS extension (for geospatial queries)
- Virtualenv
- Docker (optional for containerized deployment)
- FastAPI framework

---

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/yourusername/matching-service.git
   cd matching-service
   ```

2. **Create a Virtual Environment**:
   ```bash
   python -m venv venv
   ```

3. **Activate the Virtual Environment**:
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

4. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

## Configuration

### Environment Variables

Create a `.env` file in the project root directory with the following configuration:

```env
MONGODB_URL=mongodb://localhost:27017/
SERVICE_NAME=matchingService
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
LOG_LEVEL=INFO
```

An example configuration file is provided as `.env.example`.

### Database Setup

1. **PostgreSQL Setup**:
   - Run `init.sql` for creating tables
   - Use `dump_file.sql` to seed the database with sample data
   - Ensure the PostGIS extension is enabled for geospatial queries

2. **MongoDB Setup**:
   - Ensure MongoDB is running
   - The service will automatically create required collections

---

## Architecture

The Matching Service follows a layered architecture with clear separation of concerns:

### Service-Oriented Design
- Core services handle specific business domains (matching, quality evaluation, metrics tracking)
- Services are loosely coupled to allow for independent development and scaling

### Layer-Based Architecture
- **API Layer**: FastAPI routers handle HTTP requests and responses
- **Service Layer**: Business logic encapsulated in service classes
- **Repository Layer**: Data access logic for interacting with databases
- **Domain Layer**: Models and schemas define the data structures

### Data Processing Pipeline
- Vector embeddings for semantic understanding of text content
- Multi-metric similarity calculation combining L2 distance, cosine similarity, and inner product
- Location and keyword filtering for precise matching
- Result persistence to both JSON files and MongoDB

---

## Application Workflow

1. **Resume Processing**:
   - Resume text is converted to vector embeddings
   - Embeddings are stored for similarity matching

2. **Job Matching**:
   - The service processes the resume and matches it with job descriptions using:
     - Vector similarity calculations (L2 distance, cosine similarity, inner product)
     - Weighted combination of metrics (0.4, 0.4, 0.2 respectively)
     - Optional filtering by location, keywords, or radius

3. **Results Retrieval**:
   - Ranked job descriptions are stored in MongoDB and as JSON files
   - Results are retrieved via the API with optional filtering

4. **Quality Evaluation** (Optional):
   - Automated evaluation of match quality using LLM-based assessment
   - Manual feedback collection for validation and improvement

---

## API Endpoints

### 1. Get Job Matches

**Endpoint**:  
`GET /jobs/match`

**Description**:  
Fetches the most recent job matches for the authenticated user.

**Request Headers**:
- `accept: application/json`
- `Authorization: Bearer <JWT_TOKEN>`

**Optional Query Parameters**:
- `keywords`: list of keywords that need to be in the job description or the job title
- `country`: the country where the job is located, this filters out EVERY job which is in a different country (even remote ones)
- `city`: the city where the job is located, this filters out EVERY job which is in a different city (BUT remote jobs remain allowed)
- `offset`: the offset from the top match to start from (by default we limit to the top 50 results)
- `latitude`: the latitude of the central point of the circle
- `longitude`: the longitude of the central point of the circle
- `radius_km`: the radius (in km) of the circle

**Response Schema**:
Jobs are returned with the following structure:
```json
{
  "id": 12345,
  "title": "Software Engineer",
  "workplace_type": "Remote",
  "posted_date": "2025-02-15T12:00:00",
  "job_state": "Active",
  "description": "Detailed job description...",
  "apply_link": "https://example.com/apply",
  "company_name": "Example Corp",
  "company_logo": "https://example.com/logo.png",
  "location": "Berlin, Germany",
  "city": "Berlin",
  "country": "Germany",
  "portal": "JobBoard",
  "short_description": "Short summary of the job...",
  "field": "Software Development",
  "experience": "3-5 years",
  "score": 0.92,
  "skills_required": ["Python", "FastAPI", "PostgreSQL"]
}
```

**Example cURL**:
```bash
curl -X GET "http://localhost:9006/jobs/match?country=Germany&keywords=python&keywords=fastapi" \
  -H "accept: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### 2. Trigger Job Matching

**Endpoint**:  
`POST /jobs/match`

**Description**:  
Triggers a new job matching process for the authenticated user's resume.

**Request Headers**:
- `accept: application/json`
- `Authorization: Bearer <JWT_TOKEN>`

**Example cURL**:
```bash
curl -X POST http://localhost:9006/jobs/match \
  -H "accept: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### 3. Health Check Endpoints

**Basic Health Check**:  
`GET /health`

**Database Health**:  
`GET /health/db`

**MongoDB Health**:  
`GET /health/mongodb`

These endpoints verify the health of various system components and return appropriate status codes.

### 4. Quality Tracking Endpoints

**Evaluate Match Quality**:  
`POST /quality/evaluate`

**Submit User Feedback**:  
`POST /quality/feedback`

**Get Quality Metrics**:  
`GET /quality/metrics`

These endpoints are used for the quality tracking and evaluation system.

---

## Running the Application

### Using Python

Run the application with:

```bash
python app/main.py
```

### Using Docker

1. Build the image:
   ```bash
   docker build -t matching-service .
   ```

2. Run with Docker Compose:
   ```bash
   docker-compose up
   ```

---

## Testing

Run the test suite using:

```bash
pytest
```

For test coverage reporting:

```bash
pytest --cov=app --cov-report=html
```

### Test Coverage

Current test coverage is approximately 33% with all tests passing. Coverage highlights:

- **Well-Covered Modules (90-100%)**:
  - Schema definitions (`app/schemas/job.py`, `app/schemas/location.py`)
  - Test modules
  - Configuration (`app/core/config.py`)

- **Partially Covered Modules**:
  - Core matching logic (`app/libs/job_matcher.py` - 79%)
  - Matching service (`app/services/matching_service.py` - 59%)
  - MongoDB connection (`app/core/mongodb.py` - 77%)

- **Test Files**:
  - `app/tests/test_matcher.py`: Validates ranking and metric analysis
  - `app/tests/test_matching_service.py`: Tests matching service functionality
  - `app/test_schema_changes.py`: Verifies schema modifications

---

## Folder Structure

```plaintext
matching_service/
│
├── app/
│   ├── core/               # Core configurations and setup
│   │   ├── auth.py        # Authentication logic
│   │   ├── base.py        # SQLAlchemy base models
│   │   ├── config.py      # Configuration management
│   │   ├── database.py    # Database connection
│   │   ├── mongodb.py     # MongoDB connection
│   │   ├── security.py    # Security utilities
│   │   └── quality_tracking/ # Quality tracking interfaces
│   │
│   ├── libs/              # Utility libraries
│   │   ├── job_matcher.py # Job matching logic
│   │   └── text_embedder.py # Text embedding utilities
│   │
│   ├── log/               # Logging configuration
│   │
│   ├── models/            # SQLAlchemy models
│   │   ├── job.py         # Job data model
│   │   └── quality_tracking.py # Quality tracking models
│   │
│   ├── repositories/      # Data access layer
│   │   └── quality_tracking_repository.py # Quality data repository
│   │
│   ├── routers/           # API endpoints
│   │   ├── healthchecks/  # Health check implementations
│   │   ├── healthcheck_router.py
│   │   ├── jobs_matched_router.py
│   │   └── quality_tracking_router.py
│   │
│   ├── schemas/           # Pydantic models
│   │   ├── job.py         # Job response schema
│   │   └── location.py    # Location schema
│   │
│   ├── scripts/           # Database initialization
│   │   ├── create_quality_tracking_tables.py
│   │   └── init_db.py
│   │
│   ├── services/          # Business logic
│   │   ├── matching_service.py
│   │   ├── metrics_tracking_service.py
│   │   └── quality_evaluation_service.py
│   │
│   ├── tests/             # Test suite
│   │   ├── test_matcher.py
│   │   └── test_matching_service.py
│   │
│   ├── test_schema_changes.py # Schema validation tests
│   └── main.py           # Application entry point
│
├── OutputJobDescriptions/ # Ranked job descriptions
├── docs/                 # Documentation
│   ├── index.md
│   ├── matching_quality_system.md
│   ├── quality_tracking_plan.md
│   └── quality_tracking.md
├── memory-bank/          # Architectural documentation
├── requirements.txt      # Python dependencies
├── Dockerfile           # Docker setup
├── docker-compose.yaml  # Docker Compose configuration
├── init.sql            # Database initialization
├── dump_file.sql       # Sample data
└── README.md           # Documentation
```

---

## Quality Tracking

The Matching Service includes a comprehensive quality tracking system that:

1. **Evaluates Match Quality**:
   - Uses LLM-based assessment of resume-job matches
   - Scores matches on multiple dimensions:
     - Skill alignment (40%)
     - Experience match (40%)
     - Overall fit (20%)

2. **Collects User Feedback**:
   - Gathers manual feedback to validate automated evaluations
   - Uses feedback to improve matching algorithms

3. **Tracks Metrics**:
   - Individual match quality scores
   - Aggregate metrics across jobs and users
   - Correlation between automated scoring and user feedback

For detailed information, see the documentation in the `docs/` directory.

---

## Contributing

1. Fork the repository
2. Create a feature branch:
   ```bash
   git checkout -b feature-branch
   ```
3. Commit your changes:
   ```bash
   git commit -am 'Add new feature'
   ```
4. Push your branch:
   ```bash
   git push origin feature-branch
   ```
5. Create a Pull Request

### Development Workflow

1. Make sure tests pass before submitting PRs
2. Follow code style guidelines
3. Include test coverage for new features
4. Update documentation as necessary

---
