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

# Create authentication token
echo "Creating authentication token..."
TOKEN=$(python -c "from jose import jwt; print(jwt.encode({'sub': 'test_user'}, 'test-secret-key-for-testing', algorithm='HS256'))")
echo "Token: $TOKEN"

# Start the service in the background on port 8080
echo "Starting the service on port 8080..."
python -m app.main --port 8080 > server.log 2>&1 &
SERVER_PID=$!

# Wait for service to start up
echo "Waiting for service to start up..."
sleep 5

# Test health endpoint
echo "Testing health endpoint..."
curl -s $BASE_URL/health
echo -e "\n"

# Function to test synchronous endpoint
test_sync_endpoint() {
    echo "===== TESTING SYNCHRONOUS ENDPOINT ====="
    echo "Request file: $1"
    
    # Start timer
    start_time=$(date +%s.%N)
    
    # Execute request
    response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $TOKEN" \
        -d @$1 \
        $BASE_URL/jobs/match/legacy)
    
    # End timer
    end_time=$(date +%s.%N)
    
    # Calculate elapsed time
    elapsed=$(echo "$end_time - $start_time" | bc)
    
    # Count results
    result_count=$(echo $response | grep -o "\"id\"" | wc -l)
    
    echo "Request completed in $elapsed seconds"
    echo "Received $result_count results"
    echo -e "\n"
}

# Function to test asynchronous endpoint
test_async_endpoint() {
    echo "===== TESTING ASYNCHRONOUS ENDPOINT ====="
    echo "Request file: $1"
    
    # Start timer for initial response
    start_time=$(date +%s.%N)
    
    # Execute request
    response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $TOKEN" \
        -d @$1 \
        $BASE_URL/jobs/match)
    
    # End timer for initial response
    init_end_time=$(date +%s.%N)
    
    # Calculate elapsed time for initial response
    init_elapsed=$(echo "$init_end_time - $start_time" | bc)
    
    # Extract task ID
    task_id=$(echo $response | grep -o '"task_id":"[^"]*"' | cut -d'"' -f4)
    
    echo "Initial response received in $init_elapsed seconds"
    echo "Task ID: $task_id"
    
    if [ -z "$task_id" ]; then
        echo "No task ID received, cannot poll for results"
        return
    fi
    
    # Poll for results
    echo "Polling for results..."
    poll_start_time=$(date +%s.%N)
    status="pending"
    poll_count=0
    
    while [ "$status" == "pending" ] || [ "$status" == "processing" ]; do
        # Wait a bit between polls
        sleep 0.5
        
        # Get task status
        poll_count=$((poll_count + 1))
        status_response=$(curl -s -X GET \
            -H "Authorization: Bearer $TOKEN" \
            $BASE_URL/jobs/match/status/$task_id)
        
        status=$(echo $status_response | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
        
        echo "Poll $poll_count: Status = $status"
        
        # Break if failed or completed
        if [ "$status" == "failed" ] || [ "$status" == "completed" ] || [ "$status" == "expired" ]; then
            break
        fi
        
        # Timeout after 30 seconds
        current_time=$(date +%s.%N)
        if (( $(echo "$current_time - $poll_start_time > 30" | bc -l) )); then
            echo "Polling timed out after 30 seconds"
            break
        fi
    done
    
    # End timer for total process
    end_time=$(date +%s.%N)
    
    # Calculate elapsed times
    poll_elapsed=$(echo "$end_time - $poll_start_time" | bc)
    total_elapsed=$(echo "$end_time - $start_time" | bc)
    
    # Count results if completed
    if [ "$status" == "completed" ]; then
        result_count=$(echo $status_response | grep -o "\"id\"" | wc -l)
        echo "Received $result_count results"
    else
        echo "No results received (status: $status)"
    fi
    
    echo "Background processing completed in $poll_elapsed seconds"
    echo "Total process time: $total_elapsed seconds"
    echo "Number of polls required: $poll_count"
    echo -e "\n"
}

# Run tests for each test file
for test_file in test_resume_basic.json test_resume_ds.json test_resume_multi.json test_resume_long.json; do
    echo "=================================================="
    echo "Testing with file: $test_file"
    echo "=================================================="
    
    # Test synchronous endpoint
    test_sync_endpoint $test_file
    
    # Test asynchronous endpoint
    test_async_endpoint $test_file
    
    echo "=================================================="
    echo -e "\n"
done

# Test concurrent requests on async endpoint
echo "===== TESTING CONCURRENT REQUESTS ====="
echo "Sending 5 concurrent requests to async endpoint..."

start_time=$(date +%s.%N)

# Launch 5 concurrent requests
for i in {1..5}; do
    curl -s -X POST \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $TOKEN" \
        -d @test_resume_basic.json \
        $BASE_URL/jobs/match > "concurrent_result_$i.json" &
done

# Wait for all background processes to complete
wait

end_time=$(date +%s.%N)
concurrent_elapsed=$(echo "$end_time - $start_time" | bc)

echo "All concurrent requests initiated in $concurrent_elapsed seconds"

# Extract task IDs
task_ids=()
for i in {1..5}; do
    task_id=$(cat "concurrent_result_$i.json" | grep -o '"task_id":"[^"]*"' | cut -d'"' -f4)
    if [ ! -z "$task_id" ]; then
        task_ids+=($task_id)
    fi
done

echo "Task IDs: ${task_ids[@]}"

# Poll for all results
echo "Polling for all results..."
poll_start_time=$(date +%s.%N)

# Track completion status
completed=0
total=${#task_ids[@]}

while [ $completed -lt $total ]; do
    # Wait a bit between polls
    sleep 1
    
    # Check each task
    completed=0
    for task_id in "${task_ids[@]}"; do
        status_response=$(curl -s -X GET \
            -H "Authorization: Bearer $TOKEN" \
            $BASE_URL/jobs/match/status/$task_id)
        
        status=$(echo $status_response | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
        
        if [ "$status" == "completed" ] || [ "$status" == "failed" ] || [ "$status" == "expired" ]; then
            completed=$((completed + 1))
        fi
    done
    
    echo "Progress: $completed/$total tasks completed"
    
    # Timeout after 45 seconds
    current_time=$(date +%s.%N)
    if (( $(echo "$current_time - $poll_start_time > 45" | bc -l) )); then
        echo "Polling timed out after 45 seconds"
        break
    fi
done

# End timer for concurrent test
end_time=$(date +%s.%N)
total_concurrent_elapsed=$(echo "$end_time - $start_time" | bc)

echo "All concurrent requests completed in $total_concurrent_elapsed seconds"
echo -e "\n"

# Clean up
echo "Cleaning up..."
kill $SERVER_PID
rm test_resume_*.json
rm concurrent_result_*.json

echo "Performance tests completed!"