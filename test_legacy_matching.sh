#!/bin/bash

# Configuration
API_URL="http://172.20.8.100:8080"
AUTH_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJiYW5hbmExQGV4YW1wbGUuY29tIiwiaWQiOjQ1LCJpc19hZG1pbiI6ZmFsc2UsImV4cCI6MTc0MTM5NTA0OX0.xEG5nelrqhri_OrY2ZQpR4JjEJNLaN_gWcEjkHWVMmg"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "===== Testing Legacy Job Matching ====="
echo "API URL: $API_URL"
echo "Using authentication token: $AUTH_TOKEN"
echo

# Create test resume data
echo "Creating test resume data..."
cat << 'EOF' > test_resume.json
{
  "resume_text": "Experienced software engineer with 8 years of Python development. Skilled in FastAPI, PostgreSQL, and machine learning. Led development of recommendation systems and data pipelines at TechCorp and DataSolutions.",
  "preferred_locations": [{"country": "United States", "city": "San Francisco"}],
  "limit": 5
}
EOF

# Function to format JSON output
format_json() {
    python3 -m json.tool
}

# Execute the legacy matching request
echo "Executing legacy matching request..."
echo "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"
echo

# Add query parameters for filtering
QUERY_PARAMS="country=United%20States&city=San%20Francisco"

RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X GET \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -H "Content-Type: application/json" \
    "$API_URL/jobs/match/legacy?$QUERY_PARAMS")

# Extract status code
HTTP_STATUS=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$ d')

echo "Status Code: $HTTP_STATUS"
echo
echo "Response Body:"
echo "$BODY" | format_json

# Check if request was successful
if [ "$HTTP_STATUS" -eq 200 ]; then
    echo -e "\n${GREEN}Legacy matching request successful!${NC}"
    
    # Count matches
    MATCH_COUNT=$(echo "$BODY" | grep -o '"id":' | wc -l)
    echo "Number of matches found: $MATCH_COUNT"
    
    # Show match scores
    echo -e "\nMatch Scores:"
    echo "$BODY" | grep -o '"score":[0-9.]*' | cut -d':' -f2 | sort -rn | while read -r score; do
        echo "  Score: $score"
    done

    # Show job titles
    echo -e "\nMatched Job Titles:"
    echo "$BODY" | grep -o '"title":"[^"]*"' | cut -d'"' -f4 | while read -r title; do
        echo "  - $title"
    done
else
    echo -e "\n${RED}Legacy matching request failed!${NC}"
    echo "Error response:"
    echo "$BODY" | format_json
fi

# Clean up
rm test_resume.json

echo -e "\n===== Test Completed ====="