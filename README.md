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
```

### Database Setup

Run the SQL scripts to initialize the database:
1. Use `init.sql` for creating tables.
2. Use `dump_file.sql` to seed the database with sample data.

---

## Application Workflow

1. **API Interaction**:
   - The service processes the resume and matches it with job descriptions stored in the database.
   - Retrieve the ranked job matches via the API.

2. **Matching Logic**:
   - Analyzes and ranks resumes and job descriptions using `app/services/matching_service.py`.

---

## API Endpoints

### 1. Get Recent Job Matches

**Endpoint**:  
`GET /jobs/match`

**Description**:  
Fetches the most recent job matches for the authenticated user.

**Request Headers**:
- `accept: application/json`
- `Authorization: Bearer <JWT_TOKEN>`

**Optional Query Parameters**

- `keywords`: list of keywords that need to be in the job description or the job title
- `country`: the country where the job is located, this filters out EVERY job which is in a different country (even remote ones)
- `city`: the city where the job is located, this filters out EVERY job which is in a different city (BUT remote jobs remain allowed)
- `offset`: the offset from the top match to start from (by default we limit to the top 50 results, thus to see the further ones this parameter is needed)

Besides those, there are 3 optional parameters that, if present, specify a circle area where to limit the research for jobs. They are:
- `latitude`: the latitude of the central point of the circle
- `longitude`: the longitude of the central point of the circle
- `radius_km`: the radius (in km) of the circle

**Example cURL**:
```bash
curl -X GET http://localhost:9006/jobs/match \
-H "accept: application/json" \
-H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**With optional parameters**:
```bash
curl -X GET "http://localhost:9006/jobs/match?country=Germany&keywords=python&keywords=fastapi" \
  -H "accept: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl -X GET "http://localhost:9006/jobs/match?latitude=32.5&longitude=-96.1&radius_km=50.0" \
-H "accept: application/json" \
-H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl -X GET "http://localhost:9006/jobs/match?offset=50" \
-H "accept: application/json" \
-H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response Example**:
```json
[
  {
    "id": "c60e9663-75f5-4e46-a4f4-3d8a46c8bace",
    "job_id": "c60e9663-75f5-4e46-a4f4-3d8a46c8bace",
    "title": "Backend Developer",
    "workplace_type": "On-site",
    "field":"Software Engineering",
    "posted_date": "2024-12-03T10:00:00",
    "job_state": "Active",
    "description": "Develop and optimize backend APIs, ensure robust database management.",
    "skills_required":["Java","Spring Boot","Algorithmic skills","Pair-programming"],
    "apply_link": "https://backend.jobs/apply/789",
    "company": "Backend Gurus",
    "logo": "https://lever-client-logos.s3.us-west-2.amazonaws.com/d31c5099-0e02-425b-8d4b-807fb072d059-1599833704949.png",
    "city":"Nantes",
    "country":"France",
    "portal": "Indeed",
    "experience":"Mid-level"
    "score": 0.8
  }
]
```

![Matching 2](https://github.com/user-attachments/assets/c3f3038a-f87f-482c-89cd-3a77ab34c6a3)


---

## Running the Application

### Using Python

Run the application with:

```bash
python app/main.py
```


---

## Testing

Run the test suite using:

```bash
pytest
```

### Test Coverage

- **Matching Logic**:
  - Validates ranking and metric analysis (`app/tests/test_matcher.py`).

---

## Folder Structure

```plaintext
matching_service/
│
├── app/
│   ├── core/               # Core configurations (MongoDB setup)
│   ├── models/             # Data models (e.g., job.py)
│   ├── routers/            # API endpoints
│   ├── schemas/            # Data validation schemas
│   ├── scripts/            # Database initialization scripts
│   ├── services/           # Matching logic
│   ├── tests/              # Unit and integration tests
│   └── main.py             # Entry point of the application
│
├── OutputJobDescriptions/  # Ranked job descriptions
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker setup
├── docker-compose.yaml     # Docker Compose configuration
└── README.md               # Documentation
```

---

## Contributing

1. Fork the repository.
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
5. Create a Pull Request.

--- 
