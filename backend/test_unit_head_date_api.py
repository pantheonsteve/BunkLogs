#!/usr/bin/env python
"""
Test script for the updated Unit Head API with date parameter.
This script tests the new endpoint: /api/v1/unithead/<unithead_id>/<date>/
"""

import os
import sys
import django
from datetime import datetime

# Add the project directory to the path
sys.path.append('/app')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from rest_framework.test import force_authenticate
from bunk_logs.api.views import get_unit_head_bunks
from bunks.models import Unit, Bunk
from campers.models import Camper, CamperBunkAssignment
from bunklogs.models import BunkLog

User = get_user_model()

def test_unit_head_date_api():
    """Test the updated unit head API with date parameter."""
    print("🧪 Testing Unit Head API with Date Parameter")
    print("=" * 50)
    
    # Create test date
    test_date = "2024-06-15"
    print(f"📅 Test date: {test_date}")
    
    # Create request factory
    factory = RequestFactory()
    
    try:
        # Find or create a unit head user
        unit_head = User.objects.filter(role='Unit Head').first()
        if not unit_head:
            print("❌ No Unit Head user found. Creating one...")
            unit_head = User.objects.create_user(
                email='test.unithead@example.com',
                username='test.unithead@example.com',
                first_name='Test',
                last_name='UnitHead',
                role='Unit Head',
                password='testpass123'
            )
            print(f"✅ Created Unit Head: {unit_head.email}")
        else:
            print(f"✅ Found existing Unit Head: {unit_head.email}")
        
        # Find or create a unit managed by this unit head
        unit = Unit.objects.filter(unit_head=unit_head).first()
        if not unit:
            print("❌ No unit found for this Unit Head. Creating one...")
            unit = Unit.objects.create(
                name='Test Unit',
                unit_head=unit_head
            )
            print(f"✅ Created Unit: {unit.name}")
        else:
            print(f"✅ Found existing Unit: {unit.name}")
        
        # Check if unit has bunks
        bunks = unit.bunks.all()
        print(f"📋 Unit has {bunks.count()} bunks")
        
        if bunks.count() > 0:
            # Check for campers in the first bunk
            first_bunk = bunks.first()
            assignments = CamperBunkAssignment.objects.filter(bunk=first_bunk, is_active=True)
            print(f"👥 First bunk has {assignments.count()} active camper assignments")
            
            # Check for bunk logs on the test date
            bunk_logs = BunkLog.objects.filter(
                bunk_assignment__bunk=first_bunk,
                date=test_date
            )
            print(f"📝 Found {bunk_logs.count()} bunk logs for {test_date}")
        
        # Test the API endpoint
        print("\n🔍 Testing API Endpoint")
        print("-" * 30)
        
        # Create request with the new URL pattern
        url = f'/api/v1/unithead/{unit_head.id}/{test_date}/'
        request = factory.get(url)
        force_authenticate(request, user=unit_head)
        
        # Call the view function
        response = get_unit_head_bunks(request, str(unit_head.id), test_date)
        
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.data
            print("✅ API call successful!")
            print(f"🏢 Unit: {data.get('name', 'N/A')}")
            print(f"🏠 Number of bunks: {len(data.get('bunks', []))}")
            
            # Check if bunks have campers with bunk_log data
            for i, bunk in enumerate(data.get('bunks', [])):
                print(f"\n  🏠 Bunk {i+1}: {bunk.get('cabin_name', 'N/A')}")
                print(f"     📋 Session: {bunk.get('session_name', 'N/A')}")
                print(f"     👨‍🏫 Counselors: {len(bunk.get('counselors', []))}")
                print(f"     👥 Campers: {len(bunk.get('campers', []))}")
                
                # Check if campers have bunk_log data
                for j, camper in enumerate(bunk.get('campers', [])):
                    bunk_log = camper.get('bunk_log')
                    log_status = "✅ Has log" if bunk_log else "❌ No log"
                    print(f"       👤 {camper.get('first_name', 'N/A')} {camper.get('last_name', 'N/A')}: {log_status}")
                    
                    if bunk_log:
                        print(f"          📝 Log ID: {bunk_log.get('id', 'N/A')}")
                        print(f"          📅 Date: {bunk_log.get('date', 'N/A')}")
                        print(f"          🏥 Not on camp: {bunk_log.get('not_on_camp', 'N/A')}")
            
            print(f"\n🎉 SUCCESS: Updated API working correctly!")
            print(f"📍 New endpoint format: /api/v1/unithead/<unithead_id>/<date>/")
            print(f"✨ Campers now include bunk_log data for the specified date")
            
        else:
            print(f"❌ API call failed with status {response.status_code}")
            if hasattr(response, 'data') and 'error' in response.data:
                print(f"   Error: {response.data['error']}")
    
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_unit_head_date_api()
