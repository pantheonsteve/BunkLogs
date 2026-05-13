#!/usr/bin/env python3
"""
Test script to verify counselor bunk assignment functionality
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.insert(0, '/Users/steve.bresnick/Projects/BunkLogs/backend')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bunk_logs.settings')
django.setup()

from django.utils import timezone
from bunk_logs.users.models import User
from bunk_logs.bunklogs.models import CounselorLog
from bunk_logs.bunks.models import CounselorBunkAssignment, Bunk, Unit, Cabin, Session

def test_counselor_bunk_assignment():
    """Test the counselor bunk assignment functionality"""
    print("Testing counselor bunk assignment functionality...")
    
    # Get a counselor log (if any exist)
    counselor_log = CounselorLog.objects.first()
    if not counselor_log:
        print("No counselor logs found in the database")
        return
    
    print(f"Testing with counselor log: {counselor_log}")
    print(f"Counselor: {counselor_log.counselor.get_full_name()}")
    print(f"Date: {counselor_log.date}")
    
    # Test the new properties
    print(f"Bunk names: {counselor_log.bunk_names}")
    
    assignments = counselor_log.current_bunk_assignments
    print(f"Current assignments count: {assignments.count()}")
    
    for i, assignment in enumerate(assignments):
        print(f"  Assignment {i+1}: {assignment.bunk.name} (Primary: {assignment.is_primary})")
        print(f"    Unit: {assignment.bunk.unit.name if assignment.bunk.unit else 'None'}")
        print(f"    Cabin: {assignment.bunk.cabin.name if assignment.bunk.cabin else 'None'}")
        print(f"    Session: {assignment.bunk.session.name if assignment.bunk.session else 'None'}")
        print(f"    Date range: {assignment.start_date} to {assignment.end_date or 'Present'}")
    
    print("\nTest completed successfully!")

if __name__ == "__main__":
    test_counselor_bunk_assignment()
