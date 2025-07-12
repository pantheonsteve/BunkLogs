#!/usr/bin/env python3
import time
import requests
import json

def test_api_performance():
    print("🚀 Testing BunkLogs API Performance...")
    
    # Test the API endpoint that was slow
    base_url = "http://localhost:8000"
    
    # First, get a test user email
    try:
        response = requests.get(f"{base_url}/api/v1/users/", timeout=10)
        if response.status_code == 200:
            users = response.json()
            if users and len(users) > 0:
                test_email = users[0].get('email')
                print(f"📧 Testing with email: {test_email}")
                
                # Test the specific endpoint that was slow
                print("\n📊 Testing /api/v1/users/email/{email}/ endpoint...")
                start_time = time.time()
                
                response = requests.get(f"{base_url}/api/v1/users/email/{test_email}/", timeout=10)
                elapsed_time = time.time() - start_time
                elapsed_ms = elapsed_time * 1000
                
                print(f"⏱️ Response time: {elapsed_ms:.2f}ms")
                print(f"📋 Status code: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Response received with {len(data)} fields")
                    
                    # Check for expected fields
                    expected_fields = ['id', 'email', 'role', 'bunks', 'unit_bunks']
                    missing_fields = [field for field in expected_fields if field not in data]
                    if missing_fields:
                        print(f"⚠️ Missing fields: {missing_fields}")
                    else:
                        print("✅ All expected fields present")
                        
                    # Performance evaluation
                    if elapsed_ms < 100:
                        print("🎉 EXCELLENT: API response is very fast!")
                    elif elapsed_ms < 500:
                        print("✅ GOOD: API performance is acceptable")
                    elif elapsed_ms < 2000:
                        print("⚠️ WARNING: API is slower than ideal")
                    else:
                        print("❌ CRITICAL: API is still too slow")
                        
                else:
                    print(f"❌ API request failed: {response.text}")
            else:
                print("⚠️ No users found in API response")
        else:
            print(f"❌ Failed to get users list: {response.status_code}")
            
    except requests.exceptions.Timeout:
        print("❌ TIMEOUT: API request took longer than 10 seconds")
    except requests.exceptions.ConnectionError:
        print("❌ CONNECTION ERROR: Could not connect to API")
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    test_api_performance()
