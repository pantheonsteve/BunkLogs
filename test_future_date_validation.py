#!/usr/bin/env python3
"""
Test script to verify future date validation for counselor logs
Run this after starting the Django development server
"""

import requests
import json
from datetime import date, timedelta

# Configuration
BASE_URL = "http://127.0.0.1:8000"
API_ENDPOINT = "/api/v1/counselorlogs/"

def test_future_date_validation():
    """Test future date validation via API"""
    print("🧪 Testing Future Date Validation for Counselor Logs")
    print("=" * 50)
    
    # Note: This test requires authentication
    # In a real test, you'd need to:
    # 1. Log in as a counselor
    # 2. Get the JWT token
    # 3. Use it in the Authorization header
    
    print("⚠️  Manual Testing Required:")
    print("1. Visit http://localhost:5174/ in your browser")
    print("2. Log in as a counselor")
    print("3. Navigate to the counselor dashboard")
    print("4. Try to select future dates in the date picker")
    print("5. Verify future dates are disabled (grayed out)")
    print("6. Try creating a log for today - should work")
    print("7. Try accessing a future date URL directly")
    print("8. Verify you get redirected to today's date")
    
    print("\n🎯 Expected Behavior:")
    print("✅ Date picker disables future dates for counselors")
    print("✅ Form shows warning for future dates")
    print("✅ API rejects future-dated log creation")
    print("✅ Dashboard redirects future URLs to today")
    print("✅ Admins/staff can still select any date")
    
    # Test basic API availability
    try:
        response = requests.get(f"{BASE_URL}/api/v1/")
        if response.status_code == 200:
            print(f"\n✅ API is accessible at {BASE_URL}")
        else:
            print(f"\n❌ API returned status {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Cannot connect to {BASE_URL}")
        print("Make sure the Django development server is running")
        
    print(f"\n🌐 Frontend running at: http://localhost:5174/")
    print(f"🔧 Backend running at: {BASE_URL}")

if __name__ == "__main__":
    test_future_date_validation()
