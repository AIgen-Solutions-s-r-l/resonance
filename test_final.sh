#!/bin/bash

# Final performance test script with correct authentication token
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

# Use the provided authorization token
AUTH_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJiYW5hbmExQGV4YW1wbGUuY29tIiwiaWQiOjQ1LCJpc19hZG1pbiI6ZmFsc2UsImV4cCI6MTc0MTM5NDM3Mn0.euUezQ1y5xnb4HRkP8eo7TWIcbtK16qnfNx6d-_fx6M"
echo "Using provided authentication token: $AUTH_TOKEN"

# Test healthcheck endpoint
echo -e "\n===== Testing Healthcheck Endpoint ====="
time curl -s $BASE_URL/healthcheck
echo -e "\n"

# Test the synchronous legacy endpoint
echo -e "===== Testing Synchronous Legacy Endpoint ====="
time curl -X GET \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  "$BASE_URL/jobs/match/legacy"
echo -e "\n"

# Test the asynchronous endpoint
echo -e "===== Testing Asynchronous Endpoint ====="
RESPONSE=$(time curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
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
    -H "Authorization: Bearer $AUTH_TOKEN" \
    $BASE_URL/jobs/match/status/$TASK_ID)
  
  echo "Status response: $STATUS_RESPONSE"
  STATUS=$(echo $STATUS_RESPONSE | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
  echo "Current status: $STATUS"
  
  if [ "$COUNT" -gt 15 ]; then
    echo "Exceeded maximum poll attempts. Exiting."
    break
  fi
done

# Test concurrent requests performance
echo -e "\n===== Testing Concurrent Requests Performance ====="
echo "Sending 5 concurrent requests..."

for i in {1..5}; do
  curl -s -X POST \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -d @test_resume.json \
    $BASE_URL/jobs/match > "concurrent_result_$i.json" &
done

# Wait for all background processes to complete
wait

echo "All concurrent requests sent."

# Check results of concurrent requests
for i in {1..5}; do
  TASK_ID=$(cat "concurrent_result_$i.json" | grep -o '"task_id":"[^"]*"' | cut -d'"' -f4)
  if [ ! -z "$TASK_ID" ]; then
    echo "Request $i - Task ID: $TASK_ID"
  else
    echo "Request $i - No task ID found"
  fi
done

# Clean up
echo -e "\n===== Cleaning Up ====="
rm test_resume.json
rm -f concurrent_result_*.json
echo "Test completed!"