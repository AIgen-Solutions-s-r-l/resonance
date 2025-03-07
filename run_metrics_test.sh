#!/bin/bash

# Script to test the matching service with metrics enabled
# This script starts the StatsD server and the FastAPI application,
# performs test requests, and collects metrics

# Define constants
PORT=19001
HOST="localhost"
BASE_URL="http://$HOST:$PORT"
STATSD_PORT=8125
LOG_FILE="metrics_test.log"

# Create a temp directory for storing logs
mkdir -p logs

# Function to start the StatsD server
start_statsd_server() {
  echo "Starting simple StatsD server on port $STATSD_PORT..."
  # Start the server in a new terminal
  python simple_statsd_server.py --host 127.0.0.1 --port $STATSD_PORT --verbose > logs/statsd.log 2>&1 &
  STATSD_PID=$!
  echo "StatsD server started with PID: $STATSD_PID"
  
  # Give it a moment to start
  sleep 2
}

# Function to start the FastAPI server
start_api_server() {
  echo "Starting FastAPI server on port $PORT..."
  # Start uvicorn in the background and capture the output
  uvicorn app.main:app --host 0.0.0.0 --port $PORT > logs/api.log 2>&1 &
  SERVER_PID=$!
  echo "API server started with PID: $SERVER_PID"
  
  # Wait for server to start (max 10 seconds)
  echo "Waiting for server to start..."
  for i in {1..10}; do
    if curl -s "$BASE_URL/" > /dev/null; then
      echo "Server is up and running!"
      break
    fi
    if [ $i -eq 10 ]; then
      echo "Server failed to start within 10 seconds. Check logs/api.log for details."
      cleanup
      exit 1
    fi
    sleep 1
  done
}

# Function to generate a test JWT token (simplified version)
generate_test_token() {
  echo "Generating test JWT token..."
  
  # Check if generate_test_token.py exists, if not create a basic one
  if [ ! -f "generate_test_token.py" ]; then
    cat > generate_test_token.py << 'EOF'
#!/usr/bin/env python3
import jwt
import datetime
import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the secret key from environment
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

# Create a test payload
payload = {
    "sub": "test-user",
    "name": "Test User",
    "email": "test@example.com",
    "roles": ["user"],
    "exp": datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=30)
}

# Create the token
token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

# Print the token to stdout
print(token)
EOF
    chmod +x generate_test_token.py
  fi
  
  # Generate the token
  TOKEN=$(python generate_test_token.py)
  
  if [ -z "$TOKEN" ]; then
    echo "Failed to create test token."
    cleanup
    exit 1
  fi
  
  echo "Test token created successfully"
  echo "Token value: $TOKEN"
  
  return 0
}

# Function to test the API endpoints
test_endpoints() {
  echo "-------------- TESTING ENDPOINTS --------------"
  
  # Get the JWT token
  generate_test_token
  
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
  JOBS_RESPONSE=$(curl -s -X GET "$BASE_URL/jobs/matches" \
    -H "accept: application/json" \
    -H "Authorization: Bearer $TOKEN")
  
  # Check the response
  echo "Response from job matching endpoint: $JOBS_RESPONSE"
  echo ""
  
  # Test 3: Job matching with filters
  echo "3. Testing job matching with filters..."
  FILTERED_JOBS_RESPONSE=$(curl -s -X GET "$BASE_URL/jobs/matches?country=USA&keywords=developer" \
    -H "accept: application/json" \
    -H "Authorization: Bearer $TOKEN")
  
  # Check the response
  echo "Response from filtered job matching endpoint: $FILTERED_JOBS_RESPONSE"
  echo ""
}

# Function to clean up resources
cleanup() {
  echo "Cleaning up resources..."
  
  # Stop the API server
  if [ -n "$SERVER_PID" ]; then
    echo "Stopping API server with PID: $SERVER_PID"
    kill $SERVER_PID 2>/dev/null
    wait $SERVER_PID 2>/dev/null
  fi
  
  # Stop the StatsD server
  if [ -n "$STATSD_PID" ]; then
    echo "Stopping StatsD server with PID: $STATSD_PID"
    kill $STATSD_PID 2>/dev/null
    wait $STATSD_PID 2>/dev/null
  fi
  
  echo "Cleanup complete"
}

# Set up trap to ensure cleanup on script exit
trap cleanup EXIT

# Main execution
echo "==================================================="
echo "         Metrics Testing Script"
echo "==================================================="
echo ""

# Start the StatsD server
start_statsd_server

# Start the API server
start_api_server

# Test the endpoints
test_endpoints

# Keep the script running to collect metrics
echo "Services are running and metrics are being collected."
echo "Press Ctrl+C to stop all services and exit."
echo ""
echo "You can check the metrics in the StatsD server terminal."
echo "==================================================="

# Wait for user to press Ctrl+C
while true; do
  sleep 1
done