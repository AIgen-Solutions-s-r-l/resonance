#!/bin/bash
# A script to test the experience filter after fixing the query builder

# Generate a fresh token
echo "Generating authentication token..."
TOKEN=$(python tools/generate_test_token.py)
echo "Token: $TOKEN"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== EXPERIENCE FILTER TEST (AFTER FIX) ===${NC}"
echo ""
echo -e "${YELLOW}The query builder has been fixed to apply experience filters.${NC}"
echo -e "${YELLOW}Now let's test to verify that filters are correctly applied.${NC}"
echo ""

echo -e "${YELLOW}1. Start the service (run this in a separate terminal):${NC}"
echo "uvicorn app.main:app --port 9001 --log-level debug"
echo ""

echo -e "${YELLOW}2. Run these tests one by one and analyze the logs:${NC}"
echo ""

echo -e "${GREEN}# BASELINE: Test without any experience filter for comparison:${NC}"
echo "curl -X GET 'http://localhost:9001/jobs/match/legacy' -H \"Authorization: Bearer $TOKEN\" | python3 -m json.tool"
echo ""

echo -e "${GREEN}# Test with Mid experience level:${NC}"
echo "curl -X GET 'http://localhost:9001/jobs/match/legacy?experience=Mid' -H \"Authorization: Bearer $TOKEN\" | python3 -m json.tool"
echo ""

echo -e "${GREEN}# Test with Entry and Mid experience levels:${NC}"
echo "curl -X GET 'http://localhost:9001/jobs/match/legacy?experience=Entry&experience=Mid' -H \"Authorization: Bearer $TOKEN\" | python3 -m json.tool"
echo ""

echo -e "${GREEN}# Test with Executive level:${NC}"
echo "curl -X GET 'http://localhost:9001/jobs/match/legacy?experience=Executive' -H \"Authorization: Bearer $TOKEN\" | python3 -m json.tool"
echo ""

echo -e "${YELLOW}3. What to look for in the logs:${NC}"
echo "After running a test with experience filter, you should see:"
echo ""
echo -e "${BLUE}a) Evidence that experience parameters are received:${NC}"
echo '   "User {user_id} is requesting matched jobs (legacy endpoint)"'
echo '   Log should include: experience=[...]'
echo ""
echo -e "${BLUE}b) Evidence that experience filters are being built:${NC}"
echo '   "Building experience filters for: [...]"'
echo '   "Experience filter clause: [(j.experience = %s OR ...)]"'
echo ""
echo -e "${BLUE}c) Evidence that the SQL includes experience conditions:${NC}"
echo '   In the query, look for WHERE clauses that include j.experience conditions'
echo ""
echo -e "${BLUE}d) Comparison of result counts:${NC}"
echo '   The number of results with filters should be less than or equal to without filters'
echo ""

echo -e "${RED}REMEMBER:${NC} Only these experience values are valid:"
echo "- 'Intern'"
echo "- 'Entry'" 
echo "- 'Mid'"
echo "- 'Executive'"
echo ""

echo -e "${GREEN}If you see logs with 'Building experience filters' and experience conditions in the SQL query,${NC}"
echo -e "${GREEN}the fix was successful and the experience filter is now being correctly applied.${NC}"