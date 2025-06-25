#!/usr/bin/env python3
"""
Test script for the UnitStaffAssignment endpoint to verify it returns start_date and end_date fields.
This script helps test the /api/v1/unit-staff-assignments/{staffMember_id}/ endpoint.
"""

import requests
import json
import sys

def test_unit_staff_assignment_endpoint():
    """
    Test the UnitStaffAssignment endpoint with a sample user ID.
    """
    # Base URL - adjust if your server runs on a different port
    BASE_URL = "http://localhost:8000"
    
    # You'll need to replace this with a valid JWT token
    # You can get this from your frontend's localStorage or by making a login request
    AUTH_TOKEN = "your_jwt_token_here"
    
    # You'll need to replace this with a valid user ID that has a staff assignment
    USER_ID = 1
    
    # Headers for authentication
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Make the request
    url = f"{BASE_URL}/api/v1/unit-staff-assignments/{USER_ID}/"
    
    print(f"Testing endpoint: {url}")
    print(f"Using headers: {json.dumps({k: v[:20] + '...' if k == 'Authorization' else v for k, v in headers.items()}, indent=2)}")
    
    try:
        response = requests.get(url, headers=headers)
        
        print(f"\nResponse Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\nResponse Data:")
            print(json.dumps(data, indent=2))
            
            # Check for the required fields
            required_fields = ['start_date', 'end_date', 'staff_member_details']
            missing_fields = []
            
            for field in required_fields:
                if field not in data:
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"\n❌ Missing required fields: {missing_fields}")
            else:
                print("\n✅ All required fields are present!")
                
                # Check staff_member_details for user ID
                if 'staff_member_details' in data and 'id' in data['staff_member_details']:
                    print(f"✅ staff_member_details contains canonical user ID: {data['staff_member_details']['id']}")
                else:
                    print("❌ staff_member_details missing canonical user ID")
                    
                # Check date fields
                print(f"📅 Assignment dates: {data.get('start_date')} to {data.get('end_date', 'ongoing')}")
                
        elif response.status_code == 404:
            print(f"\n❌ User ID {USER_ID} not found or has no staff assignment")
            print("Response:", response.text)
        elif response.status_code == 401:
            print("\n❌ Authentication failed - check your JWT token")
            print("Response:", response.text)
        else:
            print(f"\n❌ Unexpected response code: {response.status_code}")
            print("Response:", response.text)
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the server. Make sure the Django server is running on localhost:8000")
    except Exception as e:
        print(f"❌ Error occurred: {str(e)}")

def print_usage():
    """Print usage instructions."""
    print("""
Usage Instructions:
1. Make sure your Django server is running: python manage.py runserver
2. Get a valid JWT token by logging in through your frontend or API
3. Update the AUTH_TOKEN variable in this script with your token
4. Update the USER_ID variable with a valid user ID that has a staff assignment
5. Run this script: python test_unit_staff_assignment_endpoint.py

To get a JWT token, you can:
- Log in through your frontend and check localStorage for the token
- Use curl to authenticate: curl -X POST http://localhost:8000/api/auth/login/ -d '{"email":"your@email.com","password":"yourpassword"}'
- Use the Django admin or shell to create a token for testing
""")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print_usage()
    else:
        test_unit_staff_assignment_endpoint()
