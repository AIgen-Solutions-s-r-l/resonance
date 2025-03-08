#!/bin/bash

# Test script for evaluating performance optimizations in the job matching service
echo "===== Job Matching Service Performance Test ====="

# Base URL
BASE_URL="http://localhost:8080"

# Create test resume data files
echo "Creating test data files..."

# Test 1: Basic resume
cat << 'EOF' > test_resume_basic.json
{
  "resume_text": "Experienced software engineer with 8 years of Python development. Skilled in FastAPI, PostgreSQL, and machine learning. Led development of recommendation systems and data pipelines at TechCorp and DataSolutions.",
  "preferred_locations": [{"country": "United States", "city": "San Francisco"}],
  "limit": 5
}
EOF

# Test 2: Data science resume with keywords
cat << 'EOF' > test_resume_ds.json
{
  "resume_text": "Data scientist with PhD in statistics. Expertise in machine learning, deep learning, and statistical modeling. Experience with Python, R, TensorFlow, and PyTorch.",
  "preferred_locations": [{"country": "United States", "city": "New York"}],
  "limit": 10,
  "keywords": ["machine learning", "data science", "statistics"]
}
EOF

# Test 3: Multiple locations resume
cat << 'EOF' > test_resume_multi.json
{
  "resume_text": "Product manager with 10 years experience in software industry. Led cross-functional teams to deliver enterprise SaaS solutions.",
  "preferred_locations": [
    {"country": "United States", "city": "Seattle"}, 
    {"country": "Canada", "city": "Vancouver"},
    {"country": "United Kingdom", "city": "London"}
  ],
  "limit": 15
}
EOF

# Test 4: Long resume
cat << 'EOF' > test_resume_long.json
{
  "resume_text": "Software engineer with extensive experience in distributed systems, cloud computing, and microservices architecture. Proficient in Java, Python, and Golang. Led the design and implementation of high-performance, scalable systems processing millions of transactions daily. Experienced in AWS, GCP, and Azure cloud platforms with particular expertise in containerization using Docker and orchestration with Kubernetes. Implemented CI/CD pipelines using Jenkins, GitHub Actions, and ArgoCD. Strong background in database technologies including PostgreSQL, MongoDB, and Redis. Contributed to open-source projects in the distributed systems space. Applied machine learning techniques to optimize system performance and resource allocation. Experienced in agile methodologies including Scrum and Kanban. Led teams of 5-10 engineers across multiple time zones. Masters degree in Computer Science with specialization in distributed computing. Published research papers on consensus algorithms and distributed data stores. Passionate about building resilient, scalable, and maintainable software systems that solve real-world problems. Strong advocate for DevOps culture and SRE practices. Experienced in implementing observability using tools like Prometheus, Grafana, and ELK stack. Skilled in performance tuning and optimization of large-scale systems. Experience with service mesh technologies like Istio and Linkerd. Implemented secure systems following industry best practices and compliance requirements including GDPR and SOC2. Mentored junior engineers and conducted technical interviews. Received awards for technical excellence and innovation. Regular speaker at technology conferences on distributed systems topics. Maintained 99.99% uptime for mission-critical systems serving global user base. Reduced system latency by 40% through careful optimization and architecture improvements. Decreased cloud infrastructure costs by 35% while increasing system capacity. Implemented advanced monitoring and alerting systems resulting in 60% faster incident response times. Collaborated with product managers and business stakeholders to align technical solutions with business goals. Strong communication skills with ability to explain complex technical concepts to non-technical audience.",
  "preferred_locations": [{"country": "United States", "city": "San Francisco"}],
  "limit": 10
}
EOF

# Test functions
run_sync_test() {
  echo "===== Running synchronous endpoint test ====="
  echo "Test file: $1"
  
  start_time=$(date +%s.%N)
  curl -s -X POST -H "Content-Type: application/json" -d @$1 $BASE_URL/jobs/match/legacy > /dev/null
  end_time=$(date +%s.%N)
  
  elapsed=$(echo "$end_time - $start_time" | bc)
  echo "Synchronous request completed in $elapsed seconds"
  echo ""
}

run_async_test() {
  echo "===== Running asynchronous endpoint test ====="
  echo "Test file: $1"
  
  # Measure time for initial response
  start_time=$(date +%s.%N)
  response=$(curl -s -X POST -H "Content-Type: application/json" -d @$1 $BASE_URL/jobs/match)
  end_time=$(date +%s.%N)
  
  elapsed=$(echo "$end_time - $start_time" | bc)
  echo "Async task creation completed in $elapsed seconds"
  
  # Extract task ID
  task_id=$(echo $response | grep -o '"task_id":"[^"]*"' | cut -d'"' -f4)
  echo "Task ID: $task_id"
  
  # Poll for results
  echo "Polling for results..."
  poll_start_time=$(date +%s.%N)
  status="pending"
  
  while [ "$status" == "pending" ] || [ "$status" == "processing" ]; do
    # Wait a bit between polls
    sleep 0.5
    
    # Get task status
    status_response=$(curl -s -X GET $BASE_URL/jobs/match/status/$task_id)
    status=$(echo $status_response | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    
    echo "Current status: $status"
    
    # Break if failed or completed
    if [ "$status" == "failed" ] || [ "$status" == "completed" ] || [ "$status" == "expired" ]; then
      break
    fi
  done
  
  poll_end_time=$(date +%s.%N)
  poll_elapsed=$(echo "$poll_end_time - $poll_start_time" | bc)
  total_elapsed=$(echo "$poll_end_time - $start_time" | bc)
  
  echo "Background processing completed in $poll_elapsed seconds"
  echo "Total process time (including API calls): $total_elapsed seconds"
  echo ""
}

# Test health endpoint
echo "Testing health endpoint..."
curl -s $BASE_URL/health
echo -e "\n"

# Test authentication token
echo "Creating auth token..."
TOKEN=$(python -c "from jose import jwt; print(jwt.encode({'sub': 'test_user'}, 'test-secret-key-for-testing', algorithm='HS256'))")
echo "Token: $TOKEN"
echo ""

# Run tests for each test case
for test_file in test_resume_basic.json test_resume_ds.json test_resume_multi.json test_resume_long.json; do
  if [ -f "$test_file" ]; then
    # Add authorization header to all requests
    export CURL_OPTS="-H 'Authorization: Bearer $TOKEN'"
    
    # Run synchronous test
    run_sync_test $test_file
    
    # Run asynchronous test
    run_async_test $test_file
    
    echo "====================================="
  else
    echo "Test file $test_file not found!"
  fi
done

# Cleanup
echo "Cleaning up test files..."
rm -f test_resume_*.json

echo "Performance tests completed!"