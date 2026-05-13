#!/usr/bin/env python
"""
Test script to verify that the duplicate entry bug fix works correctly.
This script simulates the duplicate entry scenario and checks if proper 400 errors are returned.
"""

import os
import sys
import django
from django.conf import settings

# Add the backend directory to the Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')

# Setup Django
django.setup()

from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from django.utils import timezone
from bunk_logs.campers.models import Camper, CamperBunkAssignment
from bunk_logs.bunks.models import Bunk, Unit
from bunk_logs.bunklogs.models import BunkLog

User = get_user_model()

def test_duplicate_entry_handling():
    """Test that duplicate bunk log entries return proper 400 errors instead of 500."""
    
    print("Setting up test data...")
    
    # Create test user (counselor)
    counselor = User.objects.create_user(
        email='test.counselor@example.com',
        password='testpass123',
        first_name='Test',
        last_name='Counselor',
        role='Counselor'
    )
    
    # Create test unit and bunk
    unit = Unit.objects.create(name='Test Unit')
    
    # Create session and cabin for the bunk
    from bunk_logs.bunks.models import Session, Cabin
    from datetime import timedelta
    session = Session.objects.create(
        name='Test Session 2025',
        start_date=timezone.now().date(),
        end_date=timezone.now().date() + timedelta(days=30),
        is_active=True
    )
    
    cabin = Cabin.objects.create(
        name='Test Cabin',
        capacity=10,
        location='Test Location'
    )
    
    # Create bunk with cabin and session (name is computed property)
    bunk = Bunk.objects.create(cabin=cabin, session=session, unit=unit)
    
    # Create test camper (no email field in Camper model)
    camper = Camper.objects.create(
        first_name='Test',
        last_name='Camper',
        date_of_birth=timezone.now().date() - timedelta(days=365*10)  # 10 years old
    )
    
    # Create camper bunk assignment
    assignment = CamperBunkAssignment.objects.create(
        camper=camper,
        bunk=bunk,
        is_active=True
    )
    
    # Create counselor assignment
    from bunk_logs.bunks.models import CounselorBunkAssignment
    CounselorBunkAssignment.objects.create(
        counselor=counselor,
        bunk=bunk,
        start_date=timezone.now().date()
    )
    
    print("Test data created successfully!")
    
    # Set up API client
    client = APIClient()
    client.force_authenticate(user=counselor)
    
    # First request - should succeed
    bunk_log_data = {
        'bunk_assignment': assignment.id,
        'social_score': 4,
        'behavior_score': 3,
        'participation_score': 5,
        'description': 'Test log entry'
    }
    
    print("Making first API request (should succeed)...")
    response1 = client.post('/api/v1/bunklogs/', bunk_log_data, format='json')
    print(f"First request status: {response1.status_code}")
    
    if response1.status_code == 201:
        print("✅ First request succeeded as expected")
    else:
        print(f"❌ First request failed unexpectedly: {response1.data}")
        return False
    
    # Second request with same data - should return 400 (not 500)
    print("Making second API request with same data (should return 400)...")
    response2 = client.post('/api/v1/bunklogs/', bunk_log_data, format='json')
    print(f"Second request status: {response2.status_code}")
    print(f"Second request data: {response2.data}")
    
    if response2.status_code == 400:
        print("✅ Second request correctly returned 400 Bad Request")
        
        # Check if the error message is user-friendly
        if 'already exists' in str(response2.data).lower():
            print("✅ Error message is user-friendly")
            return True
        else:
            print("⚠️  Error message could be more user-friendly")
            return True
    else:
        print(f"❌ Second request returned {response2.status_code} instead of 400")
        return False

def cleanup_test_data():
    """Clean up test data"""
    print("Cleaning up test data...")
    User.objects.filter(email='test.counselor@example.com').delete()
    Camper.objects.filter(first_name='Test', last_name='Camper').delete()
    Unit.objects.filter(name='Test Unit').delete()
    # Clean up session and cabin
    from bunk_logs.bunks.models import Session, Cabin
    Session.objects.filter(name='Test Session 2025').delete()
    Cabin.objects.filter(name='Test Cabin').delete()
    print("Cleanup completed!")

if __name__ == '__main__':
    try:
        success = test_duplicate_entry_handling()
        if success:
            print("\n🎉 Test PASSED! Duplicate entry handling is working correctly.")
        else:
            print("\n❌ Test FAILED! Duplicate entry handling needs attention.")
    except Exception as e:
        print(f"\n💥 Test ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cleanup_test_data()
