#!/usr/bin/env python3
"""
Simple script to check environment variables.
"""

import os
import dotenv

def main():
    # Load environment variables from .env file
    dotenv.load_dotenv()
    
    print("Environment variables:")
    print(f"SECRET_KEY: {os.getenv('SECRET_KEY')}")
    print(f"ALGORITHM: {os.getenv('ALGORITHM')}")

if __name__ == "__main__":
    main()