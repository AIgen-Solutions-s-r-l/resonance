#!/usr/bin/env python3
"""
Helper script to generate a JWT token for testing purposes.
This script creates a token that will work with the app's configured secret key.
"""

import sys
import datetime
import time
import os
import dotenv
from jose import jwt

def get_secret_key():
    # Load environment variables from .env file
    dotenv.load_dotenv()
    
    # Get secret key from environment variable
    secret_key = os.getenv("SECRET_KEY", "your-secret-key-here")
    print(f"Using secret key: {secret_key}")
    
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
    
    return token

if __name__ == "__main__":
    token = generate_token()
    print(token)