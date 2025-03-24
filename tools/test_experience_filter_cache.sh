#!/bin/bash
# Test script to verify experience filters work properly with caching

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Generate a fresh token
echo "Generating authentication token..."
TOKEN=$(python tools/generate_test_token.py 2>/dev/null)
if [ -z "$TOKEN" ]; then
  # Use fallback token if generation fails
  TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJiYW5hbmExQGV4YW1wbGUuY29tIiwiaWQiOjQ1LCJpc19hZG1pbiI6ZmFsc2UsImV4cCI6MTc0MjgyODUwN30.3dK2wgKNqYCZcxVjOxkS9Tu73jP14OXyh9yre49s8Kg"
fi
echo "Token: $TOKEN"
echo ""

echo -e "${YELLOW}Testing Experience Filter With Cache${NC}"
echo -e "${YELLOW}===============================${NC}"
echo ""

echo -e "${YELLOW}Instructions:${NC}"
echo "1. Start the service in another terminal: uvicorn app.main:app --port 9001 --log-level debug"
echo "2. Run this script to test experience filtering with cache"
echo "3. Check the server logs carefully to verify caching behavior"
echo ""

echo -e "${GREEN}Test 1: First request with 'Mid' experience filter${NC}"
echo -e "${BLUE}curl -X GET 'http://localhost:9001/jobs/match/legacy?experience=Mid' -H \"Authorization: Bearer $TOKEN\"${NC}"
echo "This should generate a cache MISS in the logs, and apply the filter in the database query"
echo ""
read -p "Press enter to run the first request..."
echo ""
curl -X GET "http://localhost:9001/jobs/match/legacy?experience=Mid" -H "Authorization: Bearer $TOKEN" | head -n 20
echo ""
echo ""

echo -e "${GREEN}Test 2: Same request again - should hit cache${NC}"
echo -e "${BLUE}curl -X GET 'http://localhost:9001/jobs/match/legacy?experience=Mid' -H \"Authorization: Bearer $TOKEN\"${NC}"
echo "This should generate a cache HIT in the logs, and the experience filter should be part of the cache key"
echo ""
read -p "Press enter to run the second request (cache hit)..."
echo ""
curl -X GET "http://localhost:9001/jobs/match/legacy?experience=Mid" -H "Authorization: Bearer $TOKEN" | head -n 20
echo ""
echo ""

echo -e "${GREEN}Test 3: Different experience filter - should be cache MISS${NC}"
echo -e "${BLUE}curl -X GET 'http://localhost:9001/jobs/match/legacy?experience=Entry' -H \"Authorization: Bearer $TOKEN\"${NC}"
echo "This should generate a new cache MISS due to different filter value"
echo ""
read -p "Press enter to run the third request (different filter)..."
echo ""
curl -X GET "http://localhost:9001/jobs/match/legacy?experience=Entry" -H "Authorization: Bearer $TOKEN" | head -n 20
echo ""
echo ""

echo -e "${YELLOW}What to verify in the logs:${NC}"
echo "1. First request: Look for 'Cache miss' and experience filter being applied in database query"
echo "2. Second request: Look for 'Cache hit' and verify it's using the same cache key as the first request"
echo "3. Third request: Look for 'Cache miss' and a different cache key than the first/second requests"
echo ""
echo "The key lines to look for in the logs are:"
echo " - 'CACHE CHECK: Generated cache key: ...' - should include experience parameter"
echo " - 'CACHE CHECK: Cache hit: True/False'"
echo " - '_build_experience_filters' log entries for different experience values"
echo ""