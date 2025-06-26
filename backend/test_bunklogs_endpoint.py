#!/usr/bin/env python
"""
Test script for the new BunkLogs API endpoint.
Usage: python manage.py shell < test_bunklogs_endpoint.py
"""

import os
import django
from datetime import date, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from bunk_logs.bunklogs.models import BunkLog, CounselorLog
from bunk_logs.campers.models import Camper, CamperBunkAssignment
from bunk_logs.bunks.models import Bunk, Unit
from bunk_logs.users.models import User

def test_bunklogs_endpoint():
    print("🧪 Testing BunkLogs API endpoint...")
    
    # Get or create a test date
    test_date = date.today()
    print(f"📅 Testing with date: {test_date}")
    
    # Check if we have any users
    users = User.objects.all()
    print(f"👥 Total users in database: {users.count()}")
    
    if users.exists():
        admin_user = users.filter(role='Admin').first()
        if not admin_user:
            admin_user = users.first()
        print(f"🔐 Using user: {admin_user.email} (Role: {admin_user.role})")
        
        # Create API client and authenticate
        client = APIClient()
        token, created = Token.objects.get_or_create(user=admin_user)
        client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
        
        # Test the endpoint
        url = f"/api/v1/bunklogs/all/{test_date.strftime('%Y-%m-%d')}/"
        print(f"🌐 Testing URL: {url}")
        
        response = client.get(url)
        print(f"📡 Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! Found {data.get('total_logs', 0)} logs for {data.get('date')}")
            
            if data.get('logs'):
                print("📋 Sample log structure:")
                sample_log = data['logs'][0]
                for key, value in sample_log.items():
                    print(f"  {key}: {value}")
            else:
                print("📝 No logs found for this date")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.content.decode()}")
    else:
        print("⚠️  No users found in database. Please create some test data first.")
    
    # Check database content
    print("\n📊 Database Statistics:")
    print(f"  Users: {User.objects.count()}")
    print(f"  Campers: {Camper.objects.count()}")
    print(f"  Bunks: {Bunk.objects.count()}")
    print(f"  Units: {Unit.objects.count()}")
    print(f"  Bunk Assignments: {CamperBunkAssignment.objects.count()}")
    print(f"  Bunk Logs: {BunkLog.objects.count()}")
    print(f"  Counselor Logs: {CounselorLog.objects.count()}")

if __name__ == "__main__":
    test_bunklogs_endpoint()
