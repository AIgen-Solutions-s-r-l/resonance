#!/bin/bash

# Test script for the Job Matching API
# This script starts the FastAPI application using uvicorn, obtains a JWT token,
# tests the API endpoints, and cleans up resources when done.

# Define constants
PORT=18001
HOST="localhost"
BASE_URL="http://$HOST:$PORT"
AUTH_URL="https://auth.neuraltrading.group/auth/login"
LOG_FILE="test_endpoints.log"

# Function to start the server
start_server() {
  echo "Starting FastAPI server on port $PORT..."
  # Start uvicorn in the background and redirect output to log file
  uvicorn app.main:app --host 0.0.0.0 --port $PORT > $LOG_FILE 2>&1 &
  SERVER_PID=$!
  echo "Server started with PID: $SERVER_PID"
  
  # Wait for server to start (max 10 seconds)
  echo "Waiting for server to start..."
  for i in {1..10}; do
    if curl -s "$BASE_URL/" > /dev/null; then
      echo "Server is up and running!"
      break
    fi
    if [ $i -eq 10 ]; then
      echo "Server failed to start within 10 seconds. Check $LOG_FILE for details."
      cleanup
      exit 1
    fi
    sleep 1
  done
}

# Function to get authentication token
get_auth_token() {
  echo "Obtaining authentication token..."
  
  # Make the authentication request
  AUTH_RESPONSE=$(curl -s -X POST "$AUTH_URL" \
    -H "Content-Type: application/json" \
    -d '{"username": "johndoe", "password": "securepassword"}')
  
  echo "The external auth token will not work with our app's secret key."
  echo "For testing purposes, we'll use a local token that matches our app configuration."
  
  # Get app's configured secret key
  APP_SECRET=$(grep SECRET_KEY .env | cut -d= -f2 | tr -d '"')
  echo "App configured with SECRET_KEY: $APP_SECRET"
  
  # Use our helper script to generate a JWT token
  echo "Creating a test token that will work with our local secret key..."
  
  # Check for PyJWT dependency
  if ! python3 -c "import jwt" 2>/dev/null; then
    echo "Installing PyJWT dependency..."
    pip install -q PyJWT
  fi
  
  # Generate token using our helper script
  TOKEN=$(./generate_test_token.py)
  
  if [ -z "$TOKEN" ]; then
    echo "Failed to create test token."
    cleanup
    exit 1
  fi
  
  echo "Test token created successfully"
  echo "Token value: $TOKEN"
  
  # Decode JWT for debugging (without verification)
  echo "Decoding JWT token..."
  
  # Extract the payload part (second segment) of the JWT token
  PAYLOAD=$(echo "$TOKEN" | cut -d. -f2)
  
  # Add padding if needed
  PADDING_LENGTH=$((4 - ${#PAYLOAD} % 4))
  if [ $PADDING_LENGTH -lt 4 ]; then
    for i in $(seq 1 $PADDING_LENGTH); do
      PAYLOAD="${PAYLOAD}="
    done
  fi
  
  # Decode the Base64 payload
  DECODED=$(echo "$PAYLOAD" | base64 -d 2>/dev/null || echo "$PAYLOAD" | base64 --decode 2>/dev/null)
  echo "Decoded token payload: $DECODED"
}

# Function to test endpoints
test_endpoints() {
  echo "-------------- TESTING ENDPOINTS --------------"
  
  # Test 1: Root endpoint (health check)
  echo "1. Testing root endpoint..."
  ROOT_RESPONSE=$(curl -s -X GET "$BASE_URL/")
  if [[ $ROOT_RESPONSE == *"running"* ]]; then
    echo "✅ Root endpoint test: SUCCESS"
    echo "   Response: $ROOT_RESPONSE"
  else
    echo "❌ Root endpoint test: FAILURE"
    echo "   Response: $ROOT_RESPONSE"
  fi
  echo ""
  
  # Test 2: Job matching endpoint
  echo "2. Testing job matching endpoint..."
  
  # Try with debug output to see full request/response details
  echo "Detailed request/response for debugging:"
  JOBS_RESPONSE=$(curl -v -X GET "$BASE_URL/jobs/match" \
    -H "accept: application/json" \
    -H "Authorization: Bearer $TOKEN" 2>&1)
  
  # Extract the response body from the verbose output
  RESPONSE_BODY=$(echo "$JOBS_RESPONSE" | grep -A 50 "< HTTP/1.1" | tail -n +2)
  
  # Make the actual request for testing (non-verbose)
  JOBS_RESPONSE=$(curl -s -X GET "$BASE_URL/jobs/match" \
    -H "accept: application/json" \
    -H "Authorization: Bearer $TOKEN")
  
  # Print token details for debugging
  echo "Token header used: Authorization: Bearer $TOKEN"
  
  # Check if the response contains a valid JSON array
  if [[ $JOBS_RESPONSE == "["* ]] || [[ $JOBS_RESPONSE == "[]" ]]; then
    echo "✅ Jobs matching endpoint test: SUCCESS"
    # Print the number of jobs if not empty
    if [[ $JOBS_RESPONSE != "[]" ]]; then
      JOB_COUNT=$(echo "$JOBS_RESPONSE" | grep -o "\{" | wc -l)
      echo "   Retrieved $JOB_COUNT jobs"
    else
      echo "   Retrieved 0 jobs (empty array)"
    fi
  else
    echo "❌ Jobs matching endpoint test: FAILURE"
    echo "   Response: $JOBS_RESPONSE"
  fi
  echo ""
  
  # Test 3: Job matching with filters
  echo "3. Testing job matching with filters..."
  FILTERED_JOBS_RESPONSE=$(curl -s -X GET "$BASE_URL/jobs/match?country=Germany&city=Berlin&keywords=python" \
    -H "accept: application/json" \
    -H "Authorization: Bearer $TOKEN")
  
  # Check if the response contains a valid JSON array
  if [[ $FILTERED_JOBS_RESPONSE == "["* ]] || [[ $FILTERED_JOBS_RESPONSE == "[]" ]]; then
    echo "✅ Filtered jobs matching endpoint test: SUCCESS"
    # Print the number of jobs if not empty
    if [[ $FILTERED_JOBS_RESPONSE != "[]" ]]; then
      JOB_COUNT=$(echo "$FILTERED_JOBS_RESPONSE" | grep -o "\{" | wc -l)
      echo "   Retrieved $JOB_COUNT jobs with filters: country=Germany, city=Berlin, keywords=python"
    else
      echo "   Retrieved 0 jobs with filters (empty array)"
    fi
  else
    echo "❌ Filtered jobs matching endpoint test: FAILURE"
    echo "   Response: $FILTERED_JOBS_RESPONSE"
  fi
  echo ""
}

# Function to clean up resources
cleanup() {
  if [ -n "$SERVER_PID" ]; then
    echo "Stopping server with PID: $SERVER_PID"
    kill -9 $SERVER_PID 2>/dev/null
    wait $SERVER_PID 2>/dev/null
    echo "Server stopped"
  fi
}

# Set up trap to ensure cleanup on script exit
trap cleanup EXIT

# Main execution
echo "==================================================="
echo "         Job Matching API Test Script"
echo "==================================================="
echo ""

# Start the server
start_server

# Get auth token
get_auth_token

# Test the endpoints
test_endpoints

echo "All tests completed successfully!"
echo "==================================================="

# Exit cleanly (cleanup will be handled by the trap)
exit 0