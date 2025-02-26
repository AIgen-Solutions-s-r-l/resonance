# Endpoint Testing Plan

## Overview
This document outlines the plan for creating a bash script that will test the endpoints of our Job Matching API. The script will start the FastAPI application using uvicorn on port 18001, obtain a JWT token, and then test the endpoints with the proper authentication.

## Server Setup
- The script will start the FastAPI application using uvicorn on localhost and port 18001
- The server will be started in the background to allow the script to continue with testing
- A brief pause will be added to ensure the server has time to initialize

## Authentication
- The script will make a POST request to the authentication service at https://auth.neuraltrading.group/auth/login
- Credentials used: username "johndoe", password "securepassword"
- The JWT token will be extracted from the response and stored for use in subsequent requests

## Endpoints to Test
Based on the content of curl.txt and the router implementation, the script will test:

1. Root endpoint (health check):
   - GET http://localhost:18001/
   - Expected: Service running message

2. Job matching endpoint:
   - GET http://localhost:18001/jobs/match
   - Authentication: Bearer token
   - Expected: List of jobs

3. Job matching with filters:
   - GET http://localhost:18001/jobs/match with query parameters:
     - country=Germany
     - city=Berlin
     - keywords=python
   - Authentication: Bearer token
   - Expected: Filtered list of jobs

## Error Handling
- The script will include error handling for each curl command
- If any test fails, the script will output an error message
- Each test will output its status (SUCCESS/FAILURE)

## Cleanup
- After all tests are complete, the script will terminate the uvicorn server process
- All temporary files created during testing will be cleaned up

## Implementation Details

### Bash Script Components

1. **Function to start the server:**
   ```bash
   start_server() {
     echo "Starting FastAPI server on port 18001..."
     uvicorn app.main:app --host 0.0.0.0 --port 18001 &
     SERVER_PID=$!
     echo "Server started with PID: $SERVER_PID"
     sleep 3  # Give the server time to start
   }
   ```

2. **Function to get auth token:**
   ```bash
   get_auth_token() {
     echo "Obtaining authentication token..."
     AUTH_RESPONSE=$(curl -s -X POST https://auth.neuraltrading.group/auth/login \
       -H "Content-Type: application/json" \
       -d '{"username": "johndoe", "password": "securepassword"}')
     
     TOKEN=$(echo $AUTH_RESPONSE | grep -o '"access_token":"[^"]*' | sed 's/"access_token":"//')
     
     if [ -z "$TOKEN" ]; then
       echo "Failed to obtain token"
       exit 1
     fi
     
     echo "Token obtained successfully"
   }
   ```

3. **Function to test endpoints:**
   ```bash
   test_endpoints() {
     echo "Testing root endpoint..."
     ROOT_RESPONSE=$(curl -s -X GET "http://localhost:18001/")
     if [[ $ROOT_RESPONSE == *"Matching Service is running"* ]]; then
       echo "✅ Root endpoint test: SUCCESS"
     else
       echo "❌ Root endpoint test: FAILURE"
     fi
     
     echo "Testing job matching endpoint..."
     JOBS_RESPONSE=$(curl -s -X GET "http://localhost:18001/jobs/match" \
       -H "accept: application/json" \
       -H "Authorization: Bearer $TOKEN")
     
     if [[ $JOBS_RESPONSE == *"["* ]]; then
       echo "✅ Jobs matching endpoint test: SUCCESS"
     else
       echo "❌ Jobs matching endpoint test: FAILURE"
     fi
     
     echo "Testing job matching with filters..."
     FILTERED_JOBS_RESPONSE=$(curl -s -X GET "http://localhost:18001/jobs/match?country=Germany&city=Berlin&keywords=python" \
       -H "accept: application/json" \
       -H "Authorization: Bearer $TOKEN")
     
     if [[ $FILTERED_JOBS_RESPONSE == *"["* ]]; then
       echo "✅ Filtered jobs matching endpoint test: SUCCESS"
     else
       echo "❌ Filtered jobs matching endpoint test: FAILURE"
     fi
   }
   ```

4. **Function to stop the server and clean up:**
   ```bash
   cleanup() {
     echo "Stopping server with PID: $SERVER_PID"
     kill $SERVER_PID
     wait $SERVER_PID 2>/dev/null
     echo "Server stopped"
   }
   ```

5. **Main script flow:**
   ```bash
   # Main execution
   start_server
   get_auth_token
   test_endpoints
   cleanup
   echo "All tests completed"
   ```

## Next Steps
- Implement this script in Code mode
- Execute the script to validate all endpoints
- Document any issues encountered in the testing process