#!/usr/bin/env python3
"""
Test script for camper care dashboard filtering functionality.
Tests all filter parameters: bunk, unit head help, camper care help, and score ranges.
"""

import requests
import json
import sys
from datetime import datetime, timedelta

# Container configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api"

# Test credentials
EMAIL = "cc1@clc.org"  # Camper Care user with active data
PASSWORD = "testpass123"

def get_auth_token():
    """Get authentication token."""
    token_url = f"{BASE_URL}/api/auth-token/"
    response = requests.post(token_url, {
        "username": EMAIL,  # Using email as username
        "password": PASSWORD
    })
    
    if response.status_code == 200:
        return response.json()['token']
    else:
        print(f"Authentication failed: {response.status_code}")
        print(response.text)
        return None

def test_camper_care_endpoint(token, camper_care_id, date, filters=None):
    """Test the camper care endpoint with optional filters."""
    url = f"{BASE_URL}/api/campercare/{camper_care_id}/{date}/"
    headers = {
        "Authorization": f"Token {token}",
        "Content-Type": "application/json"
    }
    
    params = filters if filters else {}
    
    print(f"\n=== Testing Camper Care Endpoint ===")
    print(f"URL: {url}")
    print(f"Filters: {params}")
    
    response = requests.get(url, headers=headers, params=params)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        # Count total campers and logs
        total_campers = 0
        total_logs = 0
        
        for unit in data:
            for bunk in unit.get('bunks', []):
                campers = bunk.get('campers', [])
                total_campers += len(campers)
                for camper in campers:
                    if camper.get('bunk_log'):
                        total_logs += 1
        
        print(f"Total units: {len(data)}")
        print(f"Total campers returned: {total_campers}")
        print(f"Total campers with logs: {total_logs}")
        
        return data
    else:
        print(f"Error: {response.text}")
        return None

def test_all_filters():
    """Test all filter combinations."""
    token = get_auth_token()
    if not token:
        print("Failed to get authentication token")
        return
    
    # Use yesterday's date for testing
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    camper_care_id = 26  # User cc1@clc.org (Camper Care role) with active data
    
    print("Testing Camper Care Dashboard Filtering")
    print("=" * 50)
    
    # Test 1: No filters (baseline)
    print("\n1. Testing with no filters (baseline)")
    baseline_data = test_camper_care_endpoint(token, camper_care_id, yesterday)
    
    if not baseline_data:
        print("Baseline test failed, stopping.")
        return
    
    # Test 2: Filter by specific bunk
    print("\n2. Testing filter by bunk ID")
    # Get first bunk ID from baseline data
    first_bunk_id = None
    if baseline_data:
        for unit in baseline_data:
            for bunk in unit.get('bunks', []):
                if bunk.get('id'):
                    first_bunk_id = bunk['id']
                    break
            if first_bunk_id:
                break
    
    if first_bunk_id:
        test_camper_care_endpoint(token, camper_care_id, yesterday, {
            'bunk_id': first_bunk_id
        })
    
    # Test 3: Filter by unit head help requested
    print("\n3. Testing filter by unit head help requested = true")
    test_camper_care_endpoint(token, camper_care_id, yesterday, {
        'unit_head_help': 'true'
    })
    
    print("\n4. Testing filter by unit head help requested = false")
    test_camper_care_endpoint(token, camper_care_id, yesterday, {
        'unit_head_help': 'false'
    })
    
    # Test 4: Filter by camper care help requested
    print("\n5. Testing filter by camper care help requested = true")
    test_camper_care_endpoint(token, camper_care_id, yesterday, {
        'camper_care_help': 'true'
    })
    
    print("\n6. Testing filter by camper care help requested = false")
    test_camper_care_endpoint(token, camper_care_id, yesterday, {
        'camper_care_help': 'false'
    })
    
    # Test 5: Filter by social score range
    print("\n7. Testing filter by social score (min=4)")
    test_camper_care_endpoint(token, camper_care_id, yesterday, {
        'social_score_min': '4'
    })
    
    print("\n8. Testing filter by social score (max=2)")
    test_camper_care_endpoint(token, camper_care_id, yesterday, {
        'social_score_max': '2'
    })
    
    print("\n9. Testing filter by social score range (2-4)")
    test_camper_care_endpoint(token, camper_care_id, yesterday, {
        'social_score_min': '2',
        'social_score_max': '4'
    })
    
    # Test 6: Filter by behavior score range
    print("\n10. Testing filter by behavior score (min=3)")
    test_camper_care_endpoint(token, camper_care_id, yesterday, {
        'behavior_score_min': '3'
    })
    
    # Test 7: Filter by participation score range
    print("\n11. Testing filter by participation score (max=3)")
    test_camper_care_endpoint(token, camper_care_id, yesterday, {
        'participation_score_max': '3'
    })
    
    # Test 8: Multiple filters combined
    print("\n12. Testing multiple filters combined")
    test_camper_care_endpoint(token, camper_care_id, yesterday, {
        'social_score_min': '3',
        'unit_head_help': 'false',
        'participation_score_min': '2'
    })
    
    print("\n=== All filter tests completed ===")

if __name__ == "__main__":
    test_all_filters()
