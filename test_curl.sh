#!/bin/bash

# Simple test script to evaluate the performance optimizations with curl
echo "===== Job Matching API Performance Test ====="

# Base URL
BASE_URL="http://localhost:8080"

# Create test resume data
echo "Creating test data..."
cat << 'EOF' > test_resume.json
{
  "resume_text": "Experienced software engineer with 8 years of Python development. Skilled in FastAPI, PostgreSQL, and machine learning. Led development of recommendation systems and data pipelines at TechCorp and DataSolutions.",
  "preferred_locations": [{"country": "United States", "city": "San Francisco"}],
  "limit": 5
}
EOF

# Create authentication token
echo "Creating authentication token..."
TOKEN=$(python -c "from jose import jwt; print(jwt.encode({'sub': 'test_user'}, 'test-secret-key-for-testing', algorithm='HS256'))")
echo "Token: $TOKEN"

# Test health endpoint
echo -e "\n===== Testing Health Endpoint ====="
curl -s $BASE_URL/health
echo -e "\n"

# Test the synchronous endpoint
echo -e "===== Testing Synchronous Endpoint ====="
time curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d @test_resume.json \
  $BASE_URL/jobs/match/legacy

echo -e "\n\n===== Testing Asynchronous Endpoint ====="
# Test the asynchronous endpoint - Initial request
echo "Sending initial request..."
RESPONSE=$(time curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d @test_resume.json \
  $BASE_URL/jobs/match)

echo "Response: $RESPONSE"

# Extract task ID
TASK_ID=$(echo $RESPONSE | grep -o '"task_id":"[^"]*"' | cut -d'"' -f4)
echo "Task ID: $TASK_ID"

if [ -z "$TASK_ID" ]; then
  echo "No task ID found in response. Exiting."
  exit 1
fi

# Poll for results
echo -e "\n===== Polling for Results ====="
STATUS="pending"
COUNT=0

while [ "$STATUS" == "pending" ] || [ "$STATUS" == "processing" ]; do
  sleep 1
  COUNT=$((COUNT + 1))
  echo "Poll attempt $COUNT..."
  
  STATUS_RESPONSE=$(curl -s -X GET \
    -H "Authorization: Bearer $TOKEN" \
    $BASE_URL/jobs/match/status/$TASK_ID)
  
  echo "Status response: $STATUS_RESPONSE"
  STATUS=$(echo $STATUS_RESPONSE | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
  echo "Current status: $STATUS"
  
  if [ "$COUNT" -gt 30 ]; then
    echo "Exceeded maximum poll attempts. Exiting."
    break
  fi
done

# Test with multiple concurrent requests
echo -e "\n===== Testing Concurrent Requests ====="
for i in {1..3}; do
  echo "Sending concurrent request $i..."
  curl -X POST \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d @test_resume.json \
    $BASE_URL/jobs/match > /dev/null &
done

# Wait for all background processes to complete
wait
echo "All concurrent requests sent."

# Clean up
echo -e "\n===== Cleaning Up ====="
rm test_resume.json
echo "Test completed!"