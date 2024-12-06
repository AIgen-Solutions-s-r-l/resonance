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
   - Upload a resume using the API endpoint.
   - The service processes the resume and matches it with job descriptions stored in the database.
   - Retrieve the ranked job matches via the API.

2. **Matching Logic**:
   - Analyzes and ranks resumes and job descriptions using `metric_analyzer.py`.

---

## API Endpoints

### 1. Upload Resume and Get Job Matches

**Endpoint**:  
`POST /jobs/match`

**Description**:  
Uploads a resume and returns ranked job descriptions based on the resume content.

**Request Headers**:
- `Content-Type: application/json`

**Request Body**:
```json
{
  "resume": "This is the plain text of the resume."
}
```

**Example cURL**:
```bash
curl -X POST http://localhost:9006/jobs/match \
-H "Content-Type: application/json" \
-d '{
  "resume": "This is the plain text of the resume."
}'
```

---

### 2. Get Matching Jobs for a Resume

**Endpoint**:  
`GET /jobs/match`

**Description**:  
Retrieves the most recent job matches for the authenticated user.

**Request Headers**:
- `accept: application/json`
- `Authorization: Bearer <JWT_TOKEN>`

**Example cURL**:
```bash
curl -X GET http://localhost:9006/jobs/match \
-H "accept: application/json" \
-H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJqb2huZG9lIiwiaWQiOjQsImlzX2FkbWluIjpmYWxzZSwiZXhwIjoxNzMzNTA5MDA1fQ.p1LAffYlQM0RcBsaHO8ujdqoTSXGPQKgotAqbG032ew"
```

---

## Running the Application

### Using Python

Run the application with:

```bash
python app/main.py
```

### Using Docker

Build and run the containerized application:

```bash
docker-compose up --build
```

Ensure MongoDB is running and accessible.

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
