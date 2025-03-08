#!/usr/bin/env python3
"""
Script to run the application with explicitly set environment variables
"""
import os
import subprocess

# Set the critical environment variables explicitly
os.environ["DATABASE_URL"] = "postgresql://testuser:testpassword@localhost:5432/postgres"

# Display the current settings
print(f"Running server with DATABASE_URL={os.environ.get('DATABASE_URL')}")

# Run uvicorn with the updated environment
subprocess.run(["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"])