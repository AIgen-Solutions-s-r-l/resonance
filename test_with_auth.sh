#!/bin/bash

# Performance test script with CORRECT authentication
echo "===== Job Matching Service Performance Test ====="

# Base URL
BASE_URL="http://localhost:8080"

# Create test resume data
echo "Creating test data files..."

# Test resume
cat << 'EOF' > test_resume.json
{
  "resume_text": "Experienced software engineer with 8 years of Python development. Skilled in FastAPI, PostgreSQL, and machine learning. Led development of recommendation systems and data pipelines at TechCorp and DataSolutions.",
  "preferred_locations": [{"country": "United States", "city": "San Francisco"}],
  "limit": 5
}
EOF

# Create proper authentication token with the required 'id' field
echo "Creating authentication token with correct fields..."
SECRET_KEY="test-secret-key-for-testing"
TOKEN=$(python -c "from jose import jwt; import datetime; print(jwt.encode({'id': 12345, 'sub': 'test_user', 'exp': datetime.datetime.now().timestamp() + 3600}, '$SECRET_KEY', algorithm='HS256'))")
echo "Token: $TOKEN"

# Test healthcheck endpoint
echo -e "\n===== Testing Healthcheck Endpoint ====="
time curl -s $BASE_URL/healthcheck

# Test the synchronous legacy endpoint
echo -e "\n===== Testing Synchronous Legacy Endpoint ====="
time curl -X GET \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/jobs/match/legacy"

# Test the asynchronous endpoint
echo -e "\n===== Testing Asynchronous Endpoint ====="
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
  
  if [ "$COUNT" -gt 10 ]; then
    echo "Exceeded maximum poll attempts. Exiting."
    break
  fi
done

# Clean up
echo -e "\n===== Cleaning Up ====="
rm test_resume.json
echo "Test completed!"