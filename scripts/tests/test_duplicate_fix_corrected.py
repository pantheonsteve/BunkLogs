#!/usr/bin/env python
"""
Test script to verify the dupli    #    # Create test cabin
    cabin = Cabin.objects.create(name="Test Cabin", capacity=20)reate test cabin with required fields
    cabin = Cabin.objects.create(
        name="Test Cabin",
        capacity=10,  # Required field
        location="Test Location"
    )te bunk log fix.
This script creates test data and attempts to create duplicate bunk logs
to verify that the second attempt returns a 400 error instead of a 500 error.
"""

import os
import sys
import django
import requests
import json
from datetime import date

# Add the backend directory to the Python path
sys.path.insert(0, '/Users/steve.bresnick/Projects/BunkLogs/backend')

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')

# Setup Django
django.setup()

# Now import Django models and other dependencies
from django.contrib.auth import get_user_model
from bunk_logs.bunks.models import Unit, Bunk, Session, Cabin
from bunk_logs.campers.models import Camper, CamperBunkAssignment
from bunk_logs.bunklogs.models import BunkLog
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

def cleanup_test_data():
    """Clean up any existing test data"""
    print("Cleaning up existing test data...")
    BunkLog.objects.filter(bunk_assignment__bunk__unit__name="Test Unit").delete()
    CamperBunkAssignment.objects.filter(bunk__unit__name="Test Unit").delete()
    Bunk.objects.filter(unit__name="Test Unit").delete()
    Unit.objects.filter(name="Test Unit").delete()
    Camper.objects.filter(first_name="Test", last_name="Camper").delete()
    User.objects.filter(email="testcounselor@example.com").delete()
    Cabin.objects.filter(name="Test Cabin").delete()
    Session.objects.filter(name="Test Session").delete()
    print("Cleanup completed.")

def create_test_data():
    """Create test data for the duplicate test"""
    print("Creating test data...")
    
    # Create a test session
    session = Session.objects.create(
        name="Test Session",
        start_date=date(2024, 7, 1),
        end_date=date(2024, 7, 31)
    )
    
    # Create a test cabin
    cabin = Cabin.objects.create(name="Test Cabin")
    
    # Create a test unit
    unit = Unit.objects.create(name="Test Unit")
    
    # Create a test bunk
    bunk = Bunk.objects.create(
        unit=unit,
        cabin=cabin,
        session=session,
        capacity=8
    )
    
    # Create a test camper
    camper = Camper.objects.create(
        first_name="Test",
        last_name="Camper",
        date_of_birth=date(2010, 5, 15)
    )
    
    # Create a camper bunk assignment
    assignment = CamperBunkAssignment.objects.create(
        camper=camper,
        bunk=bunk,
        start_date=date.today(),
        end_date=None
    )
    
    # Create a test counselor user
    counselor = User.objects.create_user(
        email="testcounselor@example.com",
        password="testpass123",
        first_name="Test",
        last_name="Counselor",
        role="Counselor"
    )
    
    print(f"Created test data:")
    print(f"  Session: {session.name} (ID: {session.id})")
    print(f"  Cabin: {cabin.name} (ID: {cabin.id})")
    print(f"  Unit: {unit.name} (ID: {unit.id})")
    print(f"  Bunk: ID {bunk.id} in {unit.name}")
    print(f"  Camper: {camper.first_name} {camper.last_name} (ID: {camper.id})")
    print(f"  Assignment: ID {assignment.id}")
    print(f"  Counselor: {counselor.email} (ID: {counselor.id})")
    
    return {
        'session': session,
        'cabin': cabin,
        'unit': unit,
        'bunk': bunk,
        'camper': camper,
        'assignment': assignment,
        'counselor': counselor
    }

def test_duplicate_creation():
    """Test creating duplicate bunk logs"""
    print("\n" + "="*60)
    print("TESTING DUPLICATE BUNK LOG CREATION")
    print("="*60)
    
    # Clean up and create test data
    cleanup_test_data()
    test_data = create_test_data()
    
    # Create API client
    client = APIClient()
    
    # Get JWT token for the counselor
    refresh = RefreshToken.for_user(test_data['counselor'])
    access_token = str(refresh.access_token)
    
    # Set authentication header
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
    
    # Prepare bunk log data
    bunk_log_data = {
        'bunk_assignment': test_data['assignment'].id,
        'social_score': 4,
        'behavior_score': 5,
        'participation_score': 3,
        'notes': 'Test bunk log entry for duplicate testing'
    }
    
    print(f"\nAttempting to create first bunk log with data:")
    print(json.dumps(bunk_log_data, indent=2))
    
    # First request - should succeed
    response1 = client.post('/api/bunklogs/', bunk_log_data, format='json')
    
    print(f"\nFirst request:")
    print(f"Status Code: {response1.status_code}")
    print(f"Response: {response1.data}")
    
    if response1.status_code in [200, 201]:
        print("✅ First bunk log created successfully")
        
        print(f"\nAttempting to create duplicate bunk log with same data...")
        
        # Second request - should fail with 400
        response2 = client.post('/api/bunklogs/', bunk_log_data, format='json')
        
        print(f"\nSecond request (duplicate):")
        print(f"Status Code: {response2.status_code}")
        print(f"Response: {response2.data}")
        
        if response2.status_code == 400:
            print("✅ Duplicate creation properly rejected with 400 status")
            
            # Check if the error message is user-friendly
            response_str = str(response2.data).lower()
            if ('duplicate' in response_str or 'already exists' in response_str or 
                'bunk log already exists' in response_str):
                print("✅ Error message is user-friendly and mentions duplication")
            else:
                print("⚠️  Error message might not be clear about duplication")
                
        elif response2.status_code == 500:
            print("❌ Duplicate creation still returns 500 error - fix not working")
        else:
            print(f"⚠️  Unexpected status code {response2.status_code} for duplicate")
            
    else:
        print(f"❌ First bunk log creation failed with status {response1.status_code}")
        print("Cannot test duplicate creation without a successful first creation")
    
    # Clean up test data
    print(f"\nCleaning up test data...")
    cleanup_test_data()
    print("Test completed.")

if __name__ == "__main__":
    test_duplicate_creation()
