#!/usr/bin/env python3
"""
Test script for the counselor logs by date endpoint using the new URL convention.
This script demonstrates how to use the new endpoint.

Usage:
    python test_counselor_logs_date_endpoint.py

Make sure your Django server is running before executing this script.
"""

import requests
import json
from datetime import datetime, timedelta

# Configuration
BASE_URL = "http://localhost:8000"  # Adjust this to your Django server URL
API_ENDPOINT = "/api/v1/counselorlogs/"

def test_counselor_logs_by_date():
    """Test the new counselor logs by date endpoint"""
    
    # Test date (today)
    test_date = datetime.now().strftime("%Y-%m-%d")
    
    # Test URL using the new convention
    url = f"{BASE_URL}{API_ENDPOINT}{test_date}/"
    
    print(f"Testing new endpoint: {url}")
    
    # You'll need to add authentication headers here
    headers = {
        'Content-Type': 'application/json',
        # Add your authentication headers here, e.g.:
        # 'Authorization': 'Bearer YOUR_JWT_TOKEN_HERE'
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success! Retrieved {data.get('total_logs', 0)} counselor logs for {test_date}")
            print(f"Response format:")
            print(f"  - date: {data.get('date')}")
            print(f"  - total_logs: {data.get('total_logs')}")
            print(f"  - results: {len(data.get('results', []))} log entries")
            
            # Show first log entry if available
            if data.get('results'):
                print(f"  - Sample log: {data['results'][0].get('id', 'N/A')}")
                
        elif response.status_code == 403:
            print("Permission denied - user role may not have access")
        elif response.status_code == 401:
            print("Authentication required - please add proper authentication headers")
        elif response.status_code == 400:
            print("Bad request - check date format")
            print(f"Error: {response.text}")
        else:
            print(f"Error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the server. Make sure your Django server is running.")
    except Exception as e:
        print(f"Unexpected error: {e}")

def test_invalid_date_format():
    """Test the endpoint with an invalid date format"""
    
    # Test with invalid date format
    invalid_date = "2025-13-45"  # Invalid date
    url = f"{BASE_URL}{API_ENDPOINT}{invalid_date}/"
    
    print(f"\nTesting invalid date format: {url}")
    
    headers = {
        'Content-Type': 'application/json',
    }
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 400:
            print("Correctly returned 400 Bad Request for invalid date format")
            print(f"Error message: {response.json()}")
        else:
            print(f"Unexpected status code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"Error testing invalid date: {e}")

def test_different_date_formats():
    """Test different date formats to verify URL routing"""
    
    test_dates = [
        "2025-06-25",  # Valid format
        "2025-12-31",  # Valid format
        "2025-01-01",  # Valid format
    ]
    
    print(f"\nTesting different valid date formats:")
    
    for test_date in test_dates:
        url = f"{BASE_URL}{API_ENDPOINT}{test_date}/"
        print(f"  Testing: {url}")
        
        try:
            response = requests.get(url, headers={'Content-Type': 'application/json'})
            print(f"    Status: {response.status_code}")
        except Exception as e:
            print(f"    Error: {e}")

if __name__ == "__main__":
    print("Testing Counselor Logs by Date Endpoint - New URL Convention")
    print("=" * 65)
    print(f"New endpoint format: {API_ENDPOINT}<YYYY-MM-DD>/")
    print(f"Example: {API_ENDPOINT}2025-06-25/")
    print("")
    
    test_counselor_logs_by_date()
    test_invalid_date_format()
    test_different_date_formats()
    
    print("\nTest completed!")
    print("\nEndpoint Summary:")
    print("- URL Format: /api/v1/counselorlogs/<YYYY-MM-DD>/")
    print("- Examples:")
    print("  * /api/v1/counselorlogs/2025-06-25/")
    print("  * /api/v1/counselorlogs/2025-12-31/")
    print("- Accessible to users with roles: Admin, Unit Head, Camper Care")
    print("- Returns JSON with date, total_logs, and results array")
    print("- Original endpoint /api/v1/counselorlogs/ still works for general listing")
    print("- Original endpoint /api/v1/counselorlogs/?date=2025-06-25 still works too")
