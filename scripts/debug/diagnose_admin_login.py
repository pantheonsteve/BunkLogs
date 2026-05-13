#!/usr/bin/env python3
"""
Direct test of admin login form to isolate the issue
"""
import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from django.test import Client
from django.contrib.admin.forms import AdminAuthenticationForm
from django.http import HttpRequest
from django.contrib.auth import get_user_model
import urllib.parse

print("=== ADMIN LOGIN DIAGNOSTIC ===")

# Test 1: Verify user exists and password works
User = get_user_model()
try:
    user = User.objects.get(email='local@bunklogs.net')
    print(f"✅ User exists: {user.email}")
    print(f"✅ Password check: {user.check_password('localadmin')}")
except User.DoesNotExist:
    print("❌ User does not exist")
    exit(1)

# Test 2: Test Django test client
print("\n=== TEST CLIENT LOGIN ===")
client = Client()

# Get login page
login_response = client.get('/admin/login/')
print(f"GET /admin/login/ status: {login_response.status_code}")

# Extract CSRF token
csrf_token = None
if 'csrftoken' in login_response.cookies:
    csrf_token = login_response.cookies['csrftoken'].value
    print(f"CSRF token from cookie: {csrf_token[:20]}...")

# Try login with test client
login_data = {
    'username': 'local@bunklogs.net',
    'password': 'localadmin',
    'next': '/admin/',
    'this_is_the_login_form': '1',
}

if csrf_token:
    login_data['csrfmiddlewaretoken'] = csrf_token

print(f"Login data: {login_data}")

post_response = client.post('/admin/login/', data=login_data)
print(f"POST /admin/login/ status: {post_response.status_code}")

if post_response.status_code == 302:
    print(f"✅ SUCCESS! Redirected to: {post_response.url}")
else:
    print("❌ FAILED - analyzing response...")
    
    # Check for form errors in context
    if hasattr(post_response, 'context') and post_response.context:
        form = post_response.context.get('form')
        if form and hasattr(form, 'errors'):
            print(f"Form errors: {form.errors}")
            print(f"Form non-field errors: {form.non_field_errors()}")
        else:
            print("No form in context or no errors")
    else:
        print("No context available")

# Test 3: Test AdminAuthenticationForm directly
print("\n=== DIRECT FORM TEST ===")
request = HttpRequest()
request.method = 'POST'
request.POST = login_data.copy()
request.META = {
    'HTTP_HOST': 'localhost:8000',
    'REMOTE_ADDR': '127.0.0.1',
}

form = AdminAuthenticationForm(request, data=login_data)
print(f"Form is_valid(): {form.is_valid()}")

if form.is_valid():
    auth_user = form.get_user()
    print(f"✅ Form authentication successful: {auth_user}")
else:
    print(f"❌ Form validation errors: {form.errors}")
    print(f"❌ Non-field errors: {form.non_field_errors()}")

print("\n=== DIAGNOSIS COMPLETE ===")
