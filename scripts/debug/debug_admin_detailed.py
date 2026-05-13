#!/usr/bin/env python
"""
Detailed Admin Login Debug - Step by step analysis
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from django.contrib.admin.forms import AdminAuthenticationForm
from django.http import HttpRequest
from django.test import RequestFactory
from django.contrib.auth import authenticate, get_user_model
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import reverse
from django.middleware.csrf import get_token

def debug_admin_login():
    print("🔍 DETAILED ADMIN LOGIN DEBUG")
    print("=" * 60)
    
    User = get_user_model()
    factory = RequestFactory()
    
    # Step 1: Verify user exists and is valid
    print("\n1. USER VERIFICATION:")
    try:
        user = User.objects.get(email='localadmin@test.com')
        print(f"✅ User: {user.email}")
        print(f"   Active: {user.is_active}")
        print(f"   Staff: {user.is_staff}")
        print(f"   Superuser: {user.is_superuser}")
        print(f"   Password check: {user.check_password('localadmin123')}")
    except User.DoesNotExist:
        print("❌ User not found")
        return False
    
    # Step 2: Test basic authentication
    print("\n2. BASIC AUTHENTICATION:")
    auth_result = authenticate(username='localadmin@test.com', password='localadmin123')
    print(f"   Result: {auth_result}")
    
    # Step 3: Test AdminAuthenticationForm step by step
    print("\n3. ADMIN FORM TESTING:")
    
    # Create a realistic request
    request = factory.post('/admin/login/', {
        'username': 'localadmin@test.com',
        'password': 'localadmin123',
        'this_is_the_login_form': '1'
    })
    request.session = {}
    request.META['REMOTE_ADDR'] = '127.0.0.1'
    request.META['HTTP_USER_AGENT'] = 'Test'
    
    form_data = {
        'username': 'localadmin@test.com',
        'password': 'localadmin123'
    }
    
    # Test the form
    form = AdminAuthenticationForm(request, data=form_data)
    print(f"   Form bound: {form.is_bound}")
    print(f"   Form valid: {form.is_valid()}")
    
    if not form.is_valid():
        print(f"   Form errors: {form.errors}")
        print(f"   Non-field errors: {form.non_field_errors()}")
        
        # Check specific validation steps
        print("\n4. DETAILED FORM VALIDATION:")
        
        # Check if user exists via form's user cache
        if hasattr(form, 'user_cache'):
            print(f"   User cache: {form.user_cache}")
        
        # Check authentication manually in form context
        username = form.cleaned_data.get('username') if form.is_bound else form_data['username']
        password = form.cleaned_data.get('password') if form.is_bound else form_data['password']
        
        print(f"   Username from form: {username}")
        print(f"   Password from form: [length={len(password)}]")
        
        # Test authentication with same parameters as form would use
        test_user = authenticate(request, username=username, password=password)
        print(f"   Manual auth with request: {test_user}")
        
        test_user2 = authenticate(username=username, password=password)
        print(f"   Manual auth without request: {test_user2}")
        
    else:
        user = form.get_user()
        print(f"✅ Form validation successful")
        print(f"   Authenticated user: {user}")
        print(f"   User is staff: {user.is_staff}")
        
    # Step 4: Check if there are any middleware issues
    print("\n5. MIDDLEWARE ANALYSIS:")
    from django.conf import settings
    for i, mw in enumerate(settings.MIDDLEWARE):
        print(f"   {i+1:2d}. {mw}")
    
    print(f"\n6. AUTHENTICATION BACKENDS:")
    for i, backend in enumerate(settings.AUTHENTICATION_BACKENDS):
        print(f"   {i+1}. {backend}")
    
    print("\n" + "=" * 60)
    
if __name__ == "__main__":
    debug_admin_login()
