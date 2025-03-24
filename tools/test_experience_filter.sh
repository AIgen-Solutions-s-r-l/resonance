#!/bin/bash
# test_experience_filter.sh - Tests the matching filter with experience using legacy endpoint

# Set your authentication token (generate or use a known token)
# You can generate a token with tools/generate_test_token.py if available
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJiYW5hbmExQGV4YW1wbGUuY29tIiwiaWQiOjQ1LCJpc19hZG1pbiI6ZmFsc2UsImV4cCI6MTc0MjgyODUwN30.3dK2wgKNqYCZcxVjOxkS9Tu73jP14OXyh9yre49s8Kg"

# Start the server (run this in a separate terminal)
echo "Run this command in a separate terminal to start the service:"
echo "uvicorn app.main:app --reload --port 9001 --log-level debug"
echo ""
echo "Then execute the following curl command to test the experience filter:"
echo ""

# Experience test cases
echo "# Test with senior experience filter:"
echo "curl -X GET 'http://localhost:9001/api/v1/jobs/match/legacy?experience=senior' \\"
echo "  -H \"Authorization: Bearer \$TOKEN\" \\"
echo "  | grep -i \"experience\""
echo ""

echo "# Test with multiple experience levels:"
echo "curl -X GET 'http://localhost:9001/api/v1/jobs/match/legacy?experience=mid-level&experience=senior' \\"
echo "  -H \"Authorization: Bearer \$TOKEN\" \\"
echo "  | grep -i \"experience\""
echo ""

echo "# After running the curl commands, check the logs for entries related to experience filtering:"
echo "grep -i \"experience\\|prefilter\" /path/to/logs/file.log"
echo ""
echo "# Or analyze the terminal output from the running server"