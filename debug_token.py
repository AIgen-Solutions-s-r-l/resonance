#!/usr/bin/env python3
"""
Debug script to validate JWT tokens and diagnose authentication issues.
"""

import sys
import jwt
from jose import jwt as jose_jwt
import os

def get_secret_key():
    """Get the secret key from .env file and directly from environment variable for comparison."""
    env_file_key = None
    env_var_key = os.getenv("SECRET_KEY")
    
    try:
        with open(".env", "r") as f:
            for line in f:
                if line.startswith("SECRET_KEY="):
                    env_file_key = line.strip().split("=", 1)[1].strip('"')
                    break
    except Exception as e:
        print(f"Error reading .env file: {e}", file=sys.stderr)
    
    print(f"Secret key from .env file: '{env_file_key}'")
    print(f"Secret key from environment: '{env_var_key}'")
    
    return env_file_key, env_var_key

def debug_token(token):
    """Examine token details and attempt to validate it with different libraries and configurations."""
    print("\n=== TOKEN DETAILS ===")
    print(f"Token: {token[:10]}...{token[-10:]}")
    
    try:
        # Get parts of the token
        header, payload, signature = token.split('.')
        print(f"\nToken parts: {len(token.split('.'))} (should be 3)")
        print(f"Header length: {len(header)}")
        print(f"Payload length: {len(payload)}")
        print(f"Signature length: {len(signature)}")
    except Exception as e:
        print(f"Error splitting token: {e}")
    
    # Get secret keys
    env_file_key, env_var_key = get_secret_key()
    
    print("\n=== DECODING ATTEMPTS ===")
    
    # Try decoding without verification
    print("\nDecoding without verification:")
    try:
        # PyJWT
        decoded = jwt.decode(token, options={"verify_signature": False})
        print(f"PyJWT decoded payload: {decoded}")
    except Exception as e:
        print(f"PyJWT decode error: {e}")
    
    try:
        # Python-JOSE
        decoded = jose_jwt.decode(token, key=None, options={"verify_signature": False})
        print(f"JOSE decoded payload: {decoded}")
    except Exception as e:
        print(f"JOSE decode error: {e}")
    
    # Try verifying with different configurations
    print("\nVerifying with .env file key:")
    try:
        # PyJWT
        decoded = jwt.decode(token, env_file_key, algorithms=["HS256"])
        print(f"PyJWT verification SUCCESS with .env file key: {decoded}")
    except Exception as e:
        print(f"PyJWT verification FAILED with .env file key: {e}")
    
    try:
        # Python-JOSE
        decoded = jose_jwt.decode(token, env_file_key, algorithms=["HS256"])
        print(f"JOSE verification SUCCESS with .env file key: {decoded}")
    except Exception as e:
        print(f"JOSE verification FAILED with .env file key: {e}")
    
    print("\nVerifying with environment variable key:")
    try:
        # PyJWT
        decoded = jwt.decode(token, env_var_key, algorithms=["HS256"])
        print(f"PyJWT verification SUCCESS with env var key: {decoded}")
    except Exception as e:
        print(f"PyJWT verification FAILED with env var key: {e}")
    
    try:
        # Python-JOSE
        decoded = jose_jwt.decode(token, env_var_key, algorithms=["HS256"])
        print(f"JOSE verification SUCCESS with env var key: {decoded}")
    except Exception as e:
        print(f"JOSE verification FAILED with env var key: {e}")

    # Test with default value
    default_key = "your-secret-key-here"
    print(f"\nVerifying with default key value: '{default_key}'")
    try:
        # PyJWT
        decoded = jwt.decode(token, default_key, algorithms=["HS256"])
        print(f"PyJWT verification SUCCESS with default key: {decoded}")
    except Exception as e:
        print(f"PyJWT verification FAILED with default key: {e}")
    
    try:
        # Python-JOSE
        decoded = jose_jwt.decode(token, default_key, algorithms=["HS256"])
        print(f"JOSE verification SUCCESS with default key: {decoded}")
    except Exception as e:
        print(f"JOSE verification FAILED with default key: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        token = sys.argv[1]
    else:
        # Generate a token
        print("No token provided. Generating a new token...")
        try:
            from generate_test_token import generate_token
            token = generate_token()
            print(f"Generated token: {token}")
        except Exception as e:
            print(f"Error generating token: {e}")
            sys.exit(1)
    
    debug_token(token)