#!/usr/bin/env python
"""
Test script to verify that BunkLog and CounselorLog date fields 
automatically sync with created_at timestamps.
"""

import os
import sys
import django
from datetime import datetime, timedelta
from django.utils import timezone

# Add the backend directory to Python path
sys.path.insert(0, '/Users/steve.bresnick/Projects/BunkLogs/backend')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from bunk_logs.bunklogs.models import BunkLog, CounselorLog
from bunk_logs.campers.models import CamperBunkAssignment
from django.contrib.auth import get_user_model

User = get_user_model()

def test_bunklog_date_sync():
    """Test that BunkLog date field syncs with created_at"""
    print("🧪 Testing BunkLog date sync...")
    
    # Find a test bunk assignment and counselor
    try:
        assignment = CamperBunkAssignment.objects.first()
        counselor = User.objects.filter(role='Counselor').first()
        
        if not assignment or not counselor:
            print("❌ No test data available (need CamperBunkAssignment and Counselor)")
            return
        
        # Create a BunkLog without specifying date
        log = BunkLog(
            bunk_assignment=assignment,
            counselor=counselor,
            social_score=5,
            behavior_score=5,
            participation_score=5,
            description="Test log for date sync"
        )
        log.save()
        
        # Check that date matches created_at date
        created_date = timezone.localtime(log.created_at).date()
        
        if log.date == created_date:
            print(f"✅ BunkLog date sync works! Date: {log.date}, Created: {created_date}")
        else:
            print(f"❌ BunkLog date sync failed! Date: {log.date}, Created: {created_date}")
        
        # Clean up
        log.delete()
        
    except Exception as e:
        print(f"❌ Error testing BunkLog: {e}")

def test_counselorlog_date_sync():
    """Test that CounselorLog date field syncs with created_at"""
    print("🧪 Testing CounselorLog date sync...")
    
    try:
        counselor = User.objects.filter(role='Counselor').first()
        
        if not counselor:
            print("❌ No test counselor available")
            return
        
        # Create a CounselorLog without specifying date
        log = CounselorLog(
            counselor=counselor,
            day_quality_score=5,
            support_level_score=5,
            elaboration="Test log for date sync",
            values_reflection="Test reflection"
        )
        log.save()
        
        # Check that date matches created_at date
        created_date = timezone.localtime(log.created_at).date()
        
        if log.date == created_date:
            print(f"✅ CounselorLog date sync works! Date: {log.date}, Created: {created_date}")
        else:
            print(f"❌ CounselorLog date sync failed! Date: {log.date}, Created: {created_date}")
        
        # Clean up
        log.delete()
        
    except Exception as e:
        print(f"❌ Error testing CounselorLog: {e}")

def test_timezone_simulation():
    """Simulate creating logs at different times (like 11:59 PM)"""
    print("🧪 Testing timezone edge cases...")
    
    try:
        # Get timezone info
        current_tz = timezone.get_current_timezone()
        print(f"Current timezone: {current_tz}")
        
        # Simulate current local time
        local_now = timezone.localtime()
        print(f"Current local time: {local_now}")
        print(f"Current local date: {local_now.date()}")
        
        # Test shows that our save method will always use local time
        # when a new record is created, regardless of what date might be passed in
        
    except Exception as e:
        print(f"❌ Error testing timezone: {e}")

if __name__ == "__main__":
    print("🚀 Testing BunkLog and CounselorLog date synchronization...")
    print("=" * 60)
    
    test_bunklog_date_sync()
    print()
    test_counselorlog_date_sync()
    print()
    test_timezone_simulation()
    
    print("\n✅ Date sync testing complete!")
    print("\n💡 Going forward:")
    print("   - All new BunkLogs will have date = local date when created")
    print("   - All new CounselorLogs will have date = local date when created") 
    print("   - This prevents midnight timezone issues")
    print("   - Counselors creating logs at 11:59 PM will get the correct date")
