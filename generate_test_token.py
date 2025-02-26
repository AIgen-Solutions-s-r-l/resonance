#!/usr/bin/env python3
"""
Helper script to generate a JWT token for testing purposes.
This script creates a token that will work with the app's configured secret key.
"""

import sys
import jwt
import datetime
import time
import os

# Read secret key from .env file
def get_secret_key():
    secret_key = "your-secret-key-here"  # Default
    
    try:
        with open(".env", "r") as f:
            for line in f:
                if line.startswith("SECRET_KEY="):
                    secret_key = line.strip().split("=", 1)[1].strip('"')
                    break
    except Exception as e:
        print(f"Error reading .env file: {e}", file=sys.stderr)
    
    return secret_key

def generate_token():
    secret_key = get_secret_key()
    
    # Set expiration time (30 minutes from now)
    exp = datetime.datetime.now() + datetime.timedelta(minutes=30)
    exp_timestamp = int(time.mktime(exp.timetuple()))
    
    # Create a payload similar to what the auth service would provide
    payload = {
        'sub': 'johndoe',
        'id': 4,
        'is_admin': False,
        'exp': exp_timestamp
    }
    
    # Sign the token with our app's secret key
    token = jwt.encode(payload, secret_key, algorithm='HS256')
    
    # If token is bytes, decode to string (PyJWT < 2.0)
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    
    return token

if __name__ == "__main__":
    token = generate_token()
    print(token)