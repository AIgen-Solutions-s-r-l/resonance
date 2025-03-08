#!/usr/bin/env python
import requests
import json
from jose import jwt
import time

# Authentication settings
SECRET_KEY = "test-secret-key-for-testing"
ALGORITHM = "HS256"
BASE_URL = "http://localhost:8080"

def create_test_token():
    """Create a test token with the required fields."""
    payload = {
        "id": 12345,  # Integer ID as required
        "sub": "test_user",
        "exp": time.time() + 3600
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    print(f"Token: {token}")
    print(f"Decoded: {jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])}")
    return token

def test_health_endpoint():
    """Test the health endpoint which doesn't require authentication."""
    response = requests.get(f"{BASE_URL}/healthcheck")
    print(f"\nHealthcheck Response: {response.status_code}")
    print(response.json())

def test_legacy_endpoint(token):
    """Test the legacy endpoint."""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/jobs/match/legacy", headers=headers)
    print(f"\nLegacy Endpoint Response: {response.status_code}")
    print(response.text)
    return response

def test_async_endpoint(token):
    """Test the async endpoint with a resume."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "resume_text": "Experienced software engineer with Python skills",
        "preferred_locations": [{"country": "United States", "city": "San Francisco"}],
        "limit": 5
    }
    response = requests.post(f"{BASE_URL}/jobs/match", headers=headers, json=data)
    print(f"\nAsync Endpoint Response: {response.status_code}")
    print(response.text)
    return response

def test_resume_endpoint(token):
    """Test if there's an endpoint to get the resume for the current user."""
    headers = {"Authorization": f"Bearer {token}"}
    # This is a guess based on the code references
    response = requests.get(f"{BASE_URL}/resume/current", headers=headers)
    print(f"\nResume Endpoint Response: {response.status_code}")
    print(response.text)

if __name__ == "__main__":
    # Create token
    token = create_test_token()
    
    # Test endpoints
    test_health_endpoint()
    test_legacy_endpoint(token)
    test_async_endpoint(token)
    test_resume_endpoint(token)