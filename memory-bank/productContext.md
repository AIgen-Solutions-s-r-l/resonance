# Product Context: Matching Service

## Project Overview
The Matching Service is a Python-based application that matches resumes with job descriptions using advanced metrics and ranking algorithms. It integrates with MongoDB for database operations and provides APIs for seamless interaction.

## Core Functionality
1. **Resume-Job Matching**: Matches resumes with job descriptions based on relevance
2. **Job Ranking**: Ranks job descriptions based on relevance to resume content
3. **API Access**: Provides endpoints for uploading resumes, retrieving matches, and accessing logs

## Technical Stack
- Python 3.12.7
- FastAPI framework
- MongoDB for document storage
- PostgreSQL for relational data
- Docker for containerization

## Data Flow
1. User resumes are processed through the API
2. Matching algorithms analyze and rank job descriptions
3. Ranked results are stored and made available through API endpoints

## Core Requirements
- Accurate matching of resumes to job descriptions
- Scalable architecture for handling multiple requests
- Secure API endpoints with proper authentication
- Monitoring and quality tracking for match effectiveness

## Memory Bank File Structure
- **activeContext.md**: Current session context and focus areas
- **productContext.md**: This file - overall project overview
- **progress.md**: Work completed and next steps
- **decisionLog.md**: Key architectural decisions and their rationale
- **systemPatterns.md**: Architectural patterns and code organization approaches

## Integration Points
- Authentication system for API access
- Database systems (MongoDB and PostgreSQL)
- Potential future integration with notification services

## Constraints
- Performance requirements for matching operations
- Security considerations for handling personal data
- Scalability needs for handling large volumes of job descriptions and resumes