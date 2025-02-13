# Matching Service

The **Matching Service** is a Python-based application that matches resumes with job descriptions using advanced metrics and ranking algorithms. It integrates with MongoDB for database operations and provides APIs for seamless interaction.

## Table of Contents

- [Overview](#overview)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Application Workflow](#application-workflow)
- [API Endpoints](#api-endpoints)
- [Running the Application](#running-the-application)
- [Testing](#testing)
- [Folder Structure](#folder-structure)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

The Matching Service facilitates the matching of resumes to job descriptions by:
1. **Ranking Job Descriptions**: Based on relevance to the resume content.
2. **Providing APIs**: For uploading resumes, retrieving job matches, and accessing logs.

---

## Requirements

- Python 3.12.7
- MongoDB server
- PostgreSQL database
- Virtualenv
- Docker (optional for containerized deployment)

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

### Database Setup

1. **PostgreSQL Setup**:
   - Run `init.sql` for creating tables
   - Use `dump_file.sql` to seed the database with sample data

2. **MongoDB Setup**:
   - Ensure MongoDB is running
   - The service will automatically create required collections

---

## Application Workflow

1. **API Interaction**:
   - The service processes the resume and matches it with job descriptions stored in the database
   - Retrieve the ranked job matches via the API

2. **Matching Logic**:
   - Analyzes and ranks resumes and job descriptions using `app/services/matching_service.py`
   - Uses text embeddings for semantic matching
   - Considers multiple metrics for ranking

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

### Test Coverage

- **Matching Logic**:
  - Validates ranking and metric analysis (`app/tests/test_matcher.py`)
  - Tests matching service functionality (`app/tests/test_matching_service.py`)

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
│   │   └── security.py    # Security utilities
│   │
│   ├── libs/              # Utility libraries
│   │   ├── job_matcher.py # Job matching logic
│   │   └── text_embedder.py # Text embedding utilities
│   │
│   ├── log/               # Logging configuration
│   │
│   ├── models/            # SQLAlchemy models
│   │
│   ├── routers/           # API endpoints
│   │   ├── healthchecks/  # Health check implementations
│   │   ├── healthcheck_router.py
│   │   └── jobs_matched_router.py
│   │
│   ├── schemas/           # Pydantic models
│   │
│   ├── scripts/           # Database initialization
│   │
│   ├── services/          # Business logic
│   │
│   ├── tests/             # Test suite
│   │
│   └── main.py           # Application entry point
│
├── OutputJobDescriptions/ # Ranked job descriptions
├── docs/                 # Documentation
├── requirements.txt      # Python dependencies
├── Dockerfile           # Docker setup
├── docker-compose.yaml  # Docker Compose configuration
└── README.md           # Documentation
```

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

---
