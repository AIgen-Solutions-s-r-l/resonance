
# Matching Service

The **Matching Service** is a Python-based application that matches resumes with job descriptions using advanced metrics and ranking algorithms. It integrates with RabbitMQ for messaging, MongoDB for database operations, and provides APIs for seamless interaction.

## Table of Contents

- [Overview](#overview)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Application Workflow](#application-workflow)
- [Running the Application](#running-the-application)
- [Testing](#testing)
- [Folder Structure](#folder-structure)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

The Matching Service facilitates matching of resumes to job descriptions by:
1. **Ranking Job Descriptions**: Based on relevance to the resume content.
2. **Providing APIs**: For interaction with external systems.
3. **Messaging**: Using RabbitMQ for processing job matching requests and responses.

---

## Requirements

- Python 3.12.7
- RabbitMQ server
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
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
MONGODB_URL=mongodb://localhost:27017/
SERVICE_NAME=matchingService
```

### Database Setup

Run the SQL scripts to initialize the database:

1. Use `init.sql` for creating tables.
2. Use `dump_file.sql` to seed the database with sample data.

---

## Application Workflow

1. **RabbitMQ Messaging**:
   - **Producer**:
     - Sends resumes and job descriptions to the queue.
   - **Consumer**:
     - Processes matching requests and responds with ranked job descriptions.

2. **Matching Logic**:
   - Analyzes and ranks resumes and job descriptions using `metric_analyzer.py`.

3. **API Interaction**:
   - Exposes endpoints for uploading resumes, retrieving job matches, and accessing logs.

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

Ensure RabbitMQ and MongoDB are running and accessible.

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
│   ├── core/               # Core configurations (RabbitMQ, MongoDB)
│   ├── models/             # Data models (e.g., job.py)
│   ├── routers/            # API endpoints
│   ├── scripts/            # Database initialization scripts
│   ├── services/           # Matching logic and messaging handlers
│   ├── tests/              # Unit and integration tests
│   └── main.py             # Entry point of the application
│
├── OutputJobDescriptions/  # Ranked job descriptions
├── OutputResumes/          # Ranked resumes
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

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.

---
