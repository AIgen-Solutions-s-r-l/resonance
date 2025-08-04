#!/bin/bash
# A script to test the experience filter with curl

# Generate a fresh token
echo "Generating authentication token..."
TOKEN=$(python tools/generate_test_token.py)
echo "Token: $TOKEN"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Testing experience filter with legacy matching endpoint${NC}"
echo ""

echo -e "${YELLOW}1. Starting service (run this in a separate terminal):${NC}"
echo "uvicorn app.main:app --port 9001 --log-level debug"
echo ""

echo -e "${YELLOW}2. Tests with correct case-sensitive experience values:${NC}"
echo ""
echo -e "${GREEN}# Test with single experience level (correct case - Mid):${NC}"
echo "curl -X GET 'http://localhost:9001/jobs/match/legacy?experience=Mid' -H \"Authorization: Bearer $TOKEN\" | python3 -m json.tool"
echo ""

echo -e "${GREEN}# Test with multiple experience levels (correct case - Entry, Mid):${NC}"
echo "curl -X GET 'http://localhost:9001/jobs/match/legacy?experience=Entry&experience=Mid' -H \"Authorization: Bearer $TOKEN\" | python3 -m json.tool"
echo ""

echo -e "${GREEN}# Test with Executive level:${NC}"
echo "curl -X GET 'http://localhost:9001/jobs/match/legacy?experience=Executive' -H \"Authorization: Bearer $TOKEN\" | python3 -m json.tool"
echo ""

echo -e "${YELLOW}3. Looking at the logs:${NC}"
echo "After running the commands, check the server logs for:"
echo "- 'Building experience filters for: [...]'"
echo "- 'Experience filter clause: [...]'"
echo "- SQL conditions with experience"
echo ""

echo -e "${RED}IMPORTANT:${NC} Based on the code analysis, only these exact values are valid:"
echo "- 'Internship'"
echo "- 'Entry'"
echo "- 'Mid'"
echo "- 'Executive'"
echo ""
echo "Using 'senior' or 'mid-level' won't work as they're not in the valid values list!"
echo ""

echo -e "${YELLOW}What to verify:${NC}"
echo "1. Check if the experience parameter is correctly received by the API"
echo "2. Look for '_build_experience_filters' being called with your experience values"
echo "3. Verify if SQL conditions like '(j.experience = %s)' are created"
echo "4. Compare the query with and without the experience filter"
echo ""

echo -e "${GREEN}If the experience filter is working correctly, you should see:${NC}"
echo "1. Log entries for 'Building experience filters'" 
echo "2. The SQL query should include WHERE conditions for experience"
echo "3. The results should be filtered to only include jobs with matching experience levels"