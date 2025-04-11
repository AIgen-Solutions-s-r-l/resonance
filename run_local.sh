#!/bin/bash

# Script to run the matching service locally for development and testing
set -e

echo "=== Running Matching Service locally for development ==="

# Build the Docker image
echo "Building Docker image..."
docker build -t matching-service-dev -f Dockerfile.dev .

# Stop and remove existing container if it exists
echo "Stopping and removing existing container if it exists..."
docker stop matching-service-dev 2>/dev/null || true
docker rm matching-service-dev 2>/dev/null || true

# Run the container
echo "Starting container on port 8002..."
docker run -d --name matching-service-dev \
  --network host \
  matching-service-dev

echo "=== Matching Service is now running locally ==="
echo "The service is available at: http://localhost:8002"
echo ""
echo "To check the status of the Docker container:"
echo "  docker ps -a | grep matching-service-dev"
echo ""
echo "To view the logs of the Docker container:"
echo "  docker logs matching-service-dev"
echo ""
echo "To stop the Docker container:"
echo "  docker stop matching-service-dev"
echo ""
echo "To restart the Docker container:"
echo "  docker start matching-service-dev"