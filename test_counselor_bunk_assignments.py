#!/usr/bin/env python3
"""
Test script to verify the CounselorLog bunk assignment functionality.
This script can be run in the Django shell or as a standalone script.
"""

import os
import sys
import django

# Add the backend directory to the Python path
sys.path.insert(0, '/Users/steve.bresnick/Projects/BunkLogs/backend')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bunk_logs.settings')
django.setup()

from django.utils import timezone
from bunk_logs.bunklogs.models import CounselorLog
from bunk_logs.api.serializers import CounselorLogSerializer

def test_counselor_log_bunk_assignments():
    """Test that counselor logs include bunk assignment information."""
    print("🧪 Testing CounselorLog bunk assignment functionality...")
    
    # Get a recent counselor log
    recent_log = CounselorLog.objects.select_related('counselor').first()
    
    if not recent_log:
        print("⚠️  No counselor logs found in the database.")
        return
    
    print(f"📋 Testing log for {recent_log.counselor.get_full_name()} on {recent_log.date}")
    
    # Test the model properties
    print(f"📍 Bunk names: {recent_log.bunk_names}")
    print(f"📍 Current bunk assignments: {recent_log.current_bunk_assignments.count()} assignment(s)")
    
    for assignment in recent_log.current_bunk_assignments:
        print(f"   - {assignment.bunk.name} ({'Primary' if assignment.is_primary else 'Secondary'})")
        print(f"     Unit: {assignment.bunk.unit.name if assignment.bunk.unit else 'No unit'}")
        print(f"     Cabin: {assignment.bunk.cabin.name if assignment.bunk.cabin else 'No cabin'}")
    
    # Test the serializer
    print("\n🔧 Testing serializer output...")
    serializer = CounselorLogSerializer(recent_log)
    data = serializer.data
    
    print(f"📄 Serialized bunk_names: {data.get('bunk_names', 'Not found')}")
    print(f"📄 Serialized bunk_assignments: {len(data.get('bunk_assignments', []))} assignment(s)")
    
    for assignment in data.get('bunk_assignments', []):
        print(f"   - {assignment.get('bunk_name')} ({'Primary' if assignment.get('is_primary') else 'Secondary'})")
        print(f"     Unit: {assignment.get('unit_name', 'No unit')}")
        print(f"     Cabin: {assignment.get('cabin_name', 'No cabin')}")
    
    print("\n✅ Test completed successfully!")

if __name__ == "__main__":
    test_counselor_log_bunk_assignments()
