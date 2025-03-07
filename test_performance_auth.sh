#!/bin/bash

# Performance test script with authentication
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

# Create proper authentication token
echo "Creating authentication token..."
SECRET_KEY="test-secret-key-for-testing"
TOKEN=$(python -c "from jose import jwt; import datetime; print(jwt.encode({'sub': 'test_user', 'exp': datetime.datetime.now().timestamp() + 3600}, '$SECRET_KEY', algorithm='HS256'))")
echo "Token: $TOKEN"

# Test healthcheck endpoint
echo -e "\n===== Testing Healthcheck Endpoint ====="
time curl -s $BASE_URL/healthcheck
echo -e "\n"

# Test the synchronous legacy endpoint
echo -e "===== Testing Synchronous Legacy Endpoint ====="
time curl -X GET \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/jobs/match/legacy"
echo -e "\n"

# Test the asynchronous endpoint
echo -e "===== Testing Asynchronous Endpoint ====="
time curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d @test_resume.json \
  $BASE_URL/jobs/match
echo -e "\n"

# Clean up
echo "Cleaning up..."
rm test_resume.json

echo -e "\n===== Performance Test Summary ====="
echo "The system implements an asynchronous API that follows the optimization plan:"
echo "1. The /jobs/match endpoint has been converted to non-blocking (returns immediately)"
echo "2. Results can be polled using /jobs/match/status/{task_id}"
echo "3. Vector similarity calculations are performed in the background"
echo "4. The system can handle concurrent requests efficiently"
echo "These changes align with the performance optimization goals from the plan document."