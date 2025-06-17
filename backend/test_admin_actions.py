#!/usr/bin/env python
"""
Test script to verify admin actions are working correctly.
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.append('/app')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from django.contrib.admin.sites import site
from bunk_logs.bunks.models import Bunk
from bunk_logs.bunks.admin import BunkAdmin
from django.test import RequestFactory

def test_admin_actions():
    """Test that admin actions are properly registered and callable."""
    
    # Create a request factory for testing
    factory = RequestFactory()
    request = factory.get('/admin/')
    
    # Get the BunkAdmin instance
    admin_instance = BunkAdmin(Bunk, site)
    
    # Get actions
    actions = admin_instance.get_actions(request)
    
    print("Available actions:")
    for action_name, action_tuple in actions.items():
        action_func, name, description = action_tuple
        print(f"  - {action_name}: {description}")
    
    # Check if our custom actions are present
    expected_actions = ['mark_as_test_data', 'mark_as_production_data', 'delete_test_data']
    for action in expected_actions:
        if action in actions:
            print(f"✓ {action} is properly registered")
        else:
            print(f"✗ {action} is missing")
    
    print("\nActions test completed!")

if __name__ == '__main__':
    test_admin_actions()
