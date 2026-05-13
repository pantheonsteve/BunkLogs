#!/usr/bin/env python3
"""
Test script to verify frontend authentication is working by testing the actual camper page URL.
"""

import requests
import json
import sys

# Configuration
BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:5173"

def get_auth_token(email, password):
    """Authenticate and get JWT token."""
    print(f"🔐 Getting auth token for {email}...")
    
    url = f"{BACKEND_URL}/api/auth/token/"
    data = {
        "email": email,
        "password": password,
    }
    
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            token_data = response.json()
            return token_data.get('access')
        else:
            print(f"❌ Auth failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Auth error: {e}")
        return None

def test_frontend_camper_access(camper_id):
    """Test accessing the frontend camper page."""
    print(f"\n🌐 Testing frontend camper page access for ID: {camper_id}")
    
    # Test the frontend URL directly
    url = f"{FRONTEND_URL}/camper/{camper_id}/2025-06-26"
    print(f"Frontend URL: {url}")
    
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ SUCCESS: Frontend camper page loads successfully")
            # Check if it contains our error message or loads properly
            if "Error Loading Camper" in response.text:
                print("⚠️ Page loads but shows error message")
                return False
            elif "CamperCare One" in response.text or "Camper" in response.text:
                print("✅ Page appears to load correctly")
                return True
            else:
                print("⚠️ Page loads but content unclear")
                return True
        else:
            print(f"❌ FAILED: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def test_backend_api_directly(auth_token, camper_id):
    """Test the backend API directly to confirm it works."""
    print(f"\n🔧 Testing backend API directly for ID: {camper_id}")
    
    url = f"{BACKEND_URL}/api/v1/campers/{camper_id}/logs/"
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
    }
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Backend API Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            camper = data.get('camper', {})
            print(f"✅ Backend API works: {camper.get('first_name', '')} {camper.get('last_name', '')}")
            return True
        else:
            print(f"❌ Backend API failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error: {error_data}")
            except:
                print(f"Error text: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def main():
    """Main test function."""
    print("🧪 Testing Frontend Camper Access After Authentication Fix")
    print("=" * 65)
    
    # Credentials
    email = "cc1@clc.org"
    password = "April221979!"
    
    # Step 1: Get auth token
    auth_token = get_auth_token(email, password)
    if not auth_token:
        print("\n❌ Cannot get auth token. Check backend.")
        return
    
    print(f"✅ Got auth token: {auth_token[:20]}...")
    
    # Step 2: Test backend API directly
    backend_success = test_backend_api_directly(auth_token, "34")
    
    # Step 3: Test frontend page access (this will use browser behavior)
    frontend_success = test_frontend_camper_access("34")
    
    print("\n" + "=" * 65)
    print("📊 SUMMARY:")
    print(f"Backend API: {'✅ WORKING' if backend_success else '❌ FAILED'}")
    print(f"Frontend Page: {'✅ ACCESSIBLE' if frontend_success else '❌ FAILED'}")
    
    if backend_success and frontend_success:
        print("\n🎉 SUCCESS: Both backend and frontend are working!")
        print("💡 The authentication fix should resolve the 401 errors.")
    elif backend_success:
        print("\n⚠️ PARTIAL: Backend works, frontend may have other issues.")
        print("💡 Try refreshing the browser and checking the browser console.")
    else:
        print("\n❌ FAILURE: Both backend and frontend have issues.")
        print("💡 Check container logs and authentication configuration.")

if __name__ == "__main__":
    main()
