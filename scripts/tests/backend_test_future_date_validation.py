#!/usr/bin/env python3
import os
import sys
import django
from datetime import date, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bunk_logs.settings.local')
django.setup()

from users.models import User
from bunklogs.models import CounselorLog

def test_future_date_validation():
    """Test that the backend prevents counselors from creating logs for future dates"""
    print("🧪 Testing future date validation...")
    
    try:
        # Get a test counselor
        counselor = User.objects.filter(role='Counselor').first()
        
        if not counselor:
            print("❌ No test counselor available")
            return
        
        # Try to create a log for tomorrow (should fail with validation)
        tomorrow = date.today() + timedelta(days=1)
        
        try:
            log = CounselorLog(
                counselor=counselor,
                date=tomorrow,  # Future date
                day_quality_score=5,
                support_level_score=5,
                elaboration="Test log for future date validation",
                values_reflection="Test reflection"
            )
            log.save()
            
            print(f"❌ VALIDATION FAILED: Log was created for future date {tomorrow}")
            log.delete()  # Clean up
            
        except Exception as e:
            if "future" in str(e).lower() or "cannot" in str(e).lower():
                print(f"✅ VALIDATION WORKING: Future date rejected - {e}")
            else:
                print(f"❓ Different error occurred: {e}")
        
        # Try to create a log for today (should succeed)
        today = date.today()
        
        try:
            log = CounselorLog(
                counselor=counselor,
                date=today,  # Today's date
                day_quality_score=5,
                support_level_score=5,
                elaboration="Test log for today's date",
                values_reflection="Test reflection"
            )
            log.save()
            
            print(f"✅ TODAY'S DATE ALLOWED: Log created successfully for {today}")
            log.delete()  # Clean up
            
        except Exception as e:
            print(f"❌ TODAY'S DATE FAILED: {e}")
        
        print("🎯 Future date validation test completed!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")

if __name__ == "__main__":
    test_future_date_validation()
