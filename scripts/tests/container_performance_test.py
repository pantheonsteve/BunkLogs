import time
from django.contrib.auth import get_user_model
from django.test.client import Client
from django.urls import reverse
import json

User = get_user_model()

def test_endpoint_performance():
    print("🚀 Testing API endpoint performance in container...")
    
    # Get a test user
    user = User.objects.first()
    if not user:
        print("❌ No users found in database")
        return
        
    print(f"📧 Testing with user: {user.email}")
    
    # Create a test client
    client = Client()
    
    # Test the endpoint that was slow
    print("\n📊 Testing /api/v1/users/email/{email}/ endpoint...")
    
    start_time = time.time()
    response = client.get(f'/api/v1/users/email/{user.email}/')
    elapsed_time = time.time() - start_time
    elapsed_ms = elapsed_time * 1000
    
    print(f"⏱️ Response time: {elapsed_ms:.2f}ms")
    print(f"📋 Status code: {response.status_code}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            print(f"✅ Response received with {len(data)} fields")
            
            # Check for expected fields
            expected_fields = ['id', 'email', 'role', 'bunks', 'unit_bunks']
            missing_fields = [field for field in expected_fields if field not in data]
            if missing_fields:
                print(f"⚠️ Missing fields: {missing_fields}")
            else:
                print("✅ All expected fields present")
                
            print(f"🔍 Response preview: {json.dumps(data, indent=2)[:500]}...")
                
        except Exception as e:
            print(f"❌ Error parsing response: {e}")
            print(f"Raw response: {response.content[:200]}")
    else:
        print(f"❌ API request failed: {response.content}")
        
    # Performance evaluation
    if elapsed_ms < 100:
        print("🎉 EXCELLENT: API response is very fast!")
    elif elapsed_ms < 500:
        print("✅ GOOD: API performance is acceptable")
    elif elapsed_ms < 2000:
        print("⚠️ WARNING: API is slower than ideal")
    else:
        print("❌ CRITICAL: API is still too slow")

if __name__ == "__main__":
    test_endpoint_performance()
