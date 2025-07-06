#!/usr/bin/env python3
"""
Test script to verify that Camper Care users can access individual camper pages
after the backend permission fix.
"""

import requests
import json
import sys

# Test configuration
BACKEND_URL = "http://localhost:8000"  # Update if your backend runs on a different port
TEST_CAMPER_ID = "1"  # Update with a real camper ID from your database

def test_camper_access(auth_token, camper_id):
    """Test accessing individual camper page with authentication."""
    url = f"{BACKEND_URL}/api/v1/camperlogs/{camper_id}/"
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
    }
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS: Camper data retrieved successfully")
            print(f"Camper: {data.get('camper', {}).get('first_name', '')} {data.get('camper', {}).get('last_name', '')}")
            print(f"Number of bunk logs: {len(data.get('bunk_logs', []))}")
            return True
        elif response.status_code == 403:
            print("❌ PERMISSION DENIED: Camper Care user cannot access this camper")
            try:
                error_data = response.json()
                print(f"Error: {error_data.get('error', 'Unknown error')}")
            except:
                print("Error response is not JSON")
            return False
        elif response.status_code == 401:
            print("❌ AUTHENTICATION FAILED: Invalid or expired token")
            return False
        elif response.status_code == 404:
            print(f"❌ NOT FOUND: Camper with ID {camper_id} not found")
            return False
        else:
            print(f"❌ UNEXPECTED ERROR: Status {response.status_code}")
            try:
                error_data = response.json()
                print(f"Response: {json.dumps(error_data, indent=2)}")
            except:
                print(f"Response text: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ CONNECTION ERROR: Cannot connect to backend at {BACKEND_URL}")
        print("Make sure the backend server is running.")
        return False
    except Exception as e:
        print(f"❌ UNEXPECTED EXCEPTION: {str(e)}")
        return False

def main():
    """Main test function."""
    print("🧪 Testing Camper Care access to individual camper pages")
    print("=" * 60)
    
    # You'll need to provide an authentication token for a Camper Care user
    auth_token = input("Enter authentication token for Camper Care user (or press Enter to skip): ").strip()
    
    if not auth_token:
        print("ℹ️  No token provided. To test properly, you need:")
        print("   1. Log in as a Camper Care user in the frontend")
        print("   2. Get the JWT token from browser dev tools")
        print("   3. Run this script with that token")
        print("\nFor now, testing with anonymous request (should fail with 401)...")
        auth_token = "invalid_token"
    
    camper_id = input(f"Enter camper ID to test (default: {TEST_CAMPER_ID}): ").strip() or TEST_CAMPER_ID
    
    print(f"\n🚀 Testing access to camper ID: {camper_id}")
    success = test_camper_access(auth_token, camper_id)
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TEST PASSED: Camper Care user can access individual camper pages")
    else:
        print("❌ TEST FAILED: Check the error messages above")
        
    print("\n📝 Notes:")
    print("   - Backend permission fix allows Camper Care users to access campers")
    print("     who have ever been assigned to bunks in their units")
    print("   - Frontend now includes clickable links to camper pages")
    print("   - Test with a real Camper Care authentication token for accurate results")

if __name__ == "__main__":
    main()
