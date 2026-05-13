#!/usr/bin/env python3
"""
Debug script to identify Django admin date display discrepancy.
This script will help us understand why the admin shows different dates than the database.
"""

import os
import sys
import django
from datetime import date, datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from bunk_logs.bunklogs.models import BunkLog
from django.utils import timezone
from django.contrib.admin.sites import site
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.conf import settings

def debug_admin_date_display():
    """Debug the admin date display issue."""
    
    print("=" * 60)
    print("DJANGO ADMIN DATE DISCREPANCY DEBUGGING")
    print("=" * 60)
    
    # 1. Database reality check
    print("\n1. DATABASE REALITY CHECK:")
    july_6 = date(2025, 7, 6)
    july_7 = date(2025, 7, 7)
    
    july_6_count = BunkLog.objects.filter(date=july_6).count()
    july_7_count = BunkLog.objects.filter(date=july_7).count()
    
    print(f"   July 6, 2025 logs: {july_6_count}")
    print(f"   July 7, 2025 logs: {july_7_count}")
    
    # 2. Admin queryset simulation
    print("\n2. ADMIN QUERYSET SIMULATION:")
    from bunk_logs.bunklogs.admin import BunkLogAdmin
    
    # Create a mock request
    factory = RequestFactory()
    request = factory.get('/admin/bunklogs/bunklog/')
    
    # Try to get a user (admin user)
    User = get_user_model()
    try:
        admin_user = User.objects.filter(is_staff=True).first()
        if admin_user:
            request.user = admin_user
            print(f"   Using admin user: {admin_user.email}")
        else:
            print("   No admin user found - creating mock user")
            request.user = User(is_staff=True, is_superuser=True, email="test@example.com")
    except Exception as e:
        print(f"   Error getting admin user: {e}")
        request.user = None
    
    # Get the admin instance
    admin_instance = BunkLogAdmin(BunkLog, site)
    
    # Test the admin queryset
    try:
        admin_queryset = admin_instance.get_queryset(request)
        print(f"   Admin queryset count: {admin_queryset.count()}")
        
        # Get the first few logs as admin would see them
        admin_logs = admin_queryset[:5]
        print("   First 5 logs as admin sees them:")
        for log in admin_logs:
            print(f"     ID: {log.id}, Date: {log.date}, Created: {log.created_at}")
            
    except Exception as e:
        print(f"   Error getting admin queryset: {e}")
    
    # 3. Admin list display simulation
    print("\n3. ADMIN LIST DISPLAY SIMULATION:")
    try:
        # Simulate what admin list_display shows
        list_display = admin_instance.list_display
        print(f"   List display fields: {list_display}")
        
        # Test the first log
        first_log = BunkLog.objects.first()
        if first_log:
            print(f"   Testing with log ID {first_log.id}:")
            
            for field_name in list_display:
                if hasattr(admin_instance, field_name):
                    # This is a method on the admin class
                    method = getattr(admin_instance, field_name)
                    try:
                        value = method(first_log)
                        print(f"     {field_name}: {value}")
                    except Exception as e:
                        print(f"     {field_name}: Error - {e}")
                else:
                    # This is a model field
                    try:
                        value = getattr(first_log, field_name)
                        print(f"     {field_name}: {value}")
                    except Exception as e:
                        print(f"     {field_name}: Error - {e}")
    except Exception as e:
        print(f"   Error in list display simulation: {e}")
    
    # 4. Check for date filtering
    print("\n4. DATE FILTERING CHECK:")
    try:
        # Check if there are any date filters applied by default
        list_filter = admin_instance.list_filter
        print(f"   List filter fields: {list_filter}")
        
        # Check for any custom filtering in changelist_view
        print("   Checking for custom changelist logic...")
        # This would require more complex simulation
        
    except Exception as e:
        print(f"   Error checking filters: {e}")
    
    # 5. Raw SQL verification
    print("\n5. RAW SQL VERIFICATION:")
    from django.db import connection
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                id, 
                date, 
                created_at,
                DATE(created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/New_York') as local_created_date
            FROM bunklogs_bunklog 
            WHERE date = %s OR date = %s
            ORDER BY created_at DESC 
            LIMIT 5
        """, [july_6, july_7])
        
        rows = cursor.fetchall()
        print("   Raw SQL results (id, date, created_at, local_created_date):")
        for row in rows:
            print(f"     {row}")
    
    # 6. Timezone investigation
    print("\n6. TIMEZONE INVESTIGATION:")
    print(f"   Current timezone: {timezone.get_current_timezone()}")
    print(f"   Current UTC time: {timezone.now()}")
    print(f"   Current local time: {timezone.localtime()}")
    print(f"   Django USE_TZ setting: {settings.USE_TZ}")
    print(f"   Django TIME_ZONE setting: {settings.TIME_ZONE}")
    
    # 7. Browser/Frontend check recommendation
    print("\n7. FRONTEND/BROWSER CHECK RECOMMENDATIONS:")
    print("   To debug the admin interface discrepancy:")
    print("   a) Clear browser cache and cookies")
    print("   b) Open Django admin in incognito/private browser")
    print("   c) Check browser dev tools for any JavaScript date manipulation")
    print("   d) Verify you're looking at the same database (check admin URL)")
    print("   e) Check if there are multiple Django instances running")
    
    # 8. Final recommendations
    print("\n8. RECOMMENDED SOLUTIONS:")
    
    if july_6_count > 0 and july_7_count == 0:
        print("   ✓ Database is correct - all logs are properly dated July 6")
        print("   ✓ The issue is likely in the admin interface display, not the data")
        print("   → Solution: Clear browser cache and check admin interface again")
        print("   → If problem persists, the issue is in frontend display logic")
    elif july_7_count > 0:
        print("   ⚠ Found logs with July 7 dates - this needs correction")
        print("   → Solution: Run date correction script")
    else:
        print("   ⚠ No logs found for July 6 or 7 - unexpected state")
    
    print("\n" + "=" * 60)
    print("DEBUG COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    debug_admin_date_display()
