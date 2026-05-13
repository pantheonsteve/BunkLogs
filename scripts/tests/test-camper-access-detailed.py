#!/usr/bin/env python3
"""
Test script to verify Camper Care API access with actual login credentials.
"""

import requests
import json
import sys

# Configuration
BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:5173"

def get_auth_token(email, password):
    """Authenticate and get JWT token."""
    print(f"🔐 Authenticating as {email}...")
    
    # Try different login endpoints that might exist
    login_endpoints = [
        "/api/auth/token/",
        "/api/auth-token/",
        "/accounts/login/",
    ]
    
    for endpoint in login_endpoints:
        url = f"{BACKEND_URL}{endpoint}"
        data = {
            "email": email,
            "password": password,
            "username": email  # Some endpoints might expect username
        }
        
        try:
            print(f"  Trying endpoint: {endpoint}")
            response = requests.post(url, json=data)
            print(f"  Status: {response.status_code}")
            
            if response.status_code == 200:
                token_data = response.json()
                print(f"  ✅ Success! Token data keys: {list(token_data.keys())}")
                
                # Extract token (could be 'access', 'token', 'access_token', etc.)
                for key in ['access', 'token', 'access_token', 'jwt']:
                    if key in token_data:
                        return token_data[key]
                
                print(f"  Full response: {json.dumps(token_data, indent=2)}")
                return None
            else:
                try:
                    error_data = response.json()
                    print(f"  Error: {error_data}")
                except:
                    print(f"  Error text: {response.text}")
                    
        except requests.exceptions.ConnectionError:
            print(f"  Connection error for {endpoint}")
        except Exception as e:
            print(f"  Exception: {str(e)}")
    
    print("❌ Could not authenticate with any endpoint")
    return None

def test_user_details(auth_token):
    """Test getting user details to verify token and role."""
    print("\n👤 Testing user details...")
    
    endpoints = [
        "/api/user/",
        "/api/v1/user/",
        "/api/users/me/",
        "/api/v1/users/me/"
    ]
    
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
    }
    
    for endpoint in endpoints:
        url = f"{BACKEND_URL}{endpoint}"
        try:
            print(f"  Trying endpoint: {endpoint}")
            response = requests.get(url, headers=headers)
            print(f"  Status: {response.status_code}")
            
            if response.status_code == 200:
                user_data = response.json()
                print(f"  ✅ User: {user_data.get('first_name', '')} {user_data.get('last_name', '')}")
                print(f"  Role: {user_data.get('role', 'Unknown')}")
                print(f"  Email: {user_data.get('email', 'Unknown')}")
                return user_data
            else:
                try:
                    error_data = response.json()
                    print(f"  Error: {error_data}")
                except:
                    print(f"  Error text: {response.text}")
                    
        except Exception as e:
            print(f"  Exception: {str(e)}")
    
    return None

def test_camper_access(auth_token, camper_id):
    """Test accessing individual camper page (frontend endpoint)."""
    print(f"\n🏕️ Testing camper logs access for ID: {camper_id} (frontend endpoint)")
    
    # Test the actual endpoint the frontend uses
    url = f"{BACKEND_URL}/api/v1/campers/{camper_id}/logs/"
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
    }
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS: Camper logs data retrieved successfully")
            camper = data.get('camper', {})
            print(f"Camper: {camper.get('first_name', '')} {camper.get('last_name', '')}")
            print(f"Number of bunk logs: {len(data.get('bunk_logs', []))}")
            print(f"Number of bunk assignments: {len(data.get('bunk_assignments', []))}")
            return True
        else:
            print("❌ FAILED")
            try:
                error_data = response.json()
                print(f"Error response: {json.dumps(error_data, indent=2)}")
            except:
                print(f"Error text: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False

def test_camper_detail_access(auth_token, camper_id):
    """Test accessing individual camper detail page."""
    print(f"\n🏕️ Testing camper detail access for ID: {camper_id}")
    
    url = f"{BACKEND_URL}/api/v1/campers/{camper_id}/"
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
    }
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS: Camper detail data retrieved successfully")
            print(f"Camper: {data.get('first_name', '')} {data.get('last_name', '')}")
            return True
        else:
            print("❌ FAILED")
            try:
                error_data = response.json()
                print(f"Error response: {json.dumps(error_data, indent=2)}")
            except:
                print(f"Error text: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False

def list_campers(auth_token):
    """List available campers to find a valid camper ID to test."""
    print("\n📋 Getting list of campers...")
    
    url = f"{BACKEND_URL}/api/v1/campers/"
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
    }
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            campers = data if isinstance(data, list) else data.get('results', [])
            print(f"Found {len(campers)} campers")
            
            if campers:
                print("First few campers:")
                for i, camper in enumerate(campers[:5]):
                    print(f"  {i+1}. ID: {camper.get('id')}, Name: {camper.get('first_name', '')} {camper.get('last_name', '')}")
                return campers[0].get('id') if campers else None
            else:
                print("No campers found")
                return None
        else:
            try:
                error_data = response.json()
                print(f"Error: {json.dumps(error_data, indent=2)}")
            except:
                print(f"Error text: {response.text}")
            return None
            
    except Exception as e:
        print(f"Exception: {str(e)}")
        return None

def main():
    """Main test function."""
    print("🧪 Testing Camper Care API Access")
    print("=" * 60)
    
    # Credentials
    email = "cc1@clc.org"
    password = "April221979!"
    
    # Step 1: Authenticate
    auth_token = get_auth_token(email, password)
    if not auth_token:
        print("\n❌ Authentication failed. Cannot proceed with tests.")
        return
    
    print(f"\n✅ Got auth token: {auth_token[:20]}...")
    
    # Step 2: Verify user details
    user_data = test_user_details(auth_token)
    if not user_data:
        print("\n⚠️ Could not get user details, but proceeding with token...")
    
    # Step 3: List campers to find a valid ID
    camper_id = list_campers(auth_token)
    if not camper_id:
        print("\n⚠️ Could not get camper list, trying with default camper ID 1...")
        camper_id = "1"
    
    # Step 4: Test camper access (both endpoints)
    success1 = test_camper_access(auth_token, camper_id)
    success2 = test_camper_detail_access(auth_token, camper_id)
    
    print("\n" + "=" * 60)
    if success1 and success2:
        print("✅ TEST PASSED: Camper Care user can access both camper logs and detail pages")
    elif success1:
        print("⚠️ PARTIAL SUCCESS: Camper logs work but detail page has issues")
    elif success2:
        print("⚠️ PARTIAL SUCCESS: Camper detail works but logs page has issues")
    else:
        print("❌ TEST FAILED: Both endpoints have permission or access issues")
        print("\nTroubleshooting:")
        print("1. Check if backend server reloaded the code changes")
        print("2. Verify the camper has assignments in units managed by this user")
        print("3. Check the backend logs for detailed error information")

if __name__ == "__main__":
    main()
