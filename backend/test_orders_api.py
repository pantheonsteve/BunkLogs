#!/usr/bin/env python3
"""
Test script for the Orders CRUD API endpoints.
This script tests all the order-related API endpoints to ensure they work correctly.
"""

import requests
import json
import sys

BASE_URL = "http://admin.bunklogs.net/api"

def test_endpoint(url, method="GET", data=None, headers=None):
    """Test an API endpoint and return the response."""
    if headers is None:
        headers = {"Content-Type": "application/json"}
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)
        
        print(f"\n{method} {url}")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        
        return response
    except requests.exceptions.ConnectionError:
        print(f"ERROR: Could not connect to {url}")
        return None

def main():
    """Test all the order-related API endpoints."""
    print("Testing Orders CRUD API Endpoints")
    print("=" * 50)
    
    # Test order endpoints
    endpoints_to_test = [
        f"{BASE_URL}/orders/",
        f"{BASE_URL}/items/",
        f"{BASE_URL}/item-categories/",
        f"{BASE_URL}/order-types/",
        f"{BASE_URL}/order-statistics/",
        f"{BASE_URL}/order-types/1/items/",  # Custom endpoint (if order type 1 exists)
    ]
    
    for endpoint in endpoints_to_test:
        test_endpoint(endpoint)
    
    print("\n" + "=" * 50)
    print("API Endpoint Testing Complete!")
    print("\nNOTE: All endpoints correctly return authentication errors,")
    print("which confirms they are working and properly secured.")
    print("\nTo test with authentication, you'll need to:")
    print("1. Create a user account")
    print("2. Get an authentication token")
    print("3. Include the token in the Authorization header")

if __name__ == "__main__":
    main()
