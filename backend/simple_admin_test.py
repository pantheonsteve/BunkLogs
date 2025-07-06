#!/usr/bin/env python
"""
Simple admin login test script
Run this inside the container to test admin functionality
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

def test_simple_admin():
    print("🔧 SIMPLE ADMIN LOGIN TEST")
    print("=" * 40)
    
    # Create a test client
    client = Client()
    
    # Test credentials
    username = 'localadmin@test.com'
    password = 'localadmin123'
    
    print(f"Testing with: {username}")
    
    # Try direct login
    login_success = client.login(username=username, password=password)
    print(f"Login success: {login_success}")
    
    if login_success:
        # Try to access admin
        response = client.get('/admin/')
        print(f"Admin access: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ SUCCESS: Admin access works with test client!")
            print("\n🎯 SOLUTION: The Django admin backend is working")
            print("💡 The issue is with HTTP session handling in the container")
            print("\n📋 RECOMMENDATION:")
            print("1. Use the working production admin for now")
            print("2. Or create a simple admin interface bypass")
            
            return True
    
    print("❌ Even test client failed")
    return False

if __name__ == "__main__":
    test_simple_admin()
