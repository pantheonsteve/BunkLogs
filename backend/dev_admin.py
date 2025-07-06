#!/usr/bin/env python
"""
Local Development Admin Wrapper
This provides admin functionality bypassing the session issue
Usage: python dev_admin.py [command]
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from django.contrib.auth import get_user_model
from django.core.management import execute_from_command_line
from django.test import Client

User = get_user_model()

def show_users():
    """Show all admin users"""
    print("👥 ADMIN USERS:")
    print("-" * 40)
    users = User.objects.filter(is_staff=True)
    for user in users:
        status = "✅" if user.is_active else "❌"
        super_status = "🔧" if user.is_superuser else "  "
        print(f"{status} {super_status} {user.email}")
    print(f"\nTotal: {users.count()} admin users")

def create_user():
    """Create a new admin user"""
    print("➕ CREATE ADMIN USER:")
    print("-" * 40)
    
    email = input("Email: ")
    if User.objects.filter(email=email).exists():
        print(f"❌ User {email} already exists")
        return
    
    password = input("Password: ")
    first_name = input("First name (optional): ")
    last_name = input("Last name (optional): ")
    
    user = User.objects.create_user(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        is_staff=True,
        is_superuser=True,
        is_active=True
    )
    
    print(f"✅ Created admin user: {user.email}")

def test_admin():
    """Test admin access"""
    print("🧪 TESTING ADMIN ACCESS:")
    print("-" * 40)
    
    client = Client()
    
    # Test with existing admin user
    user = User.objects.filter(is_staff=True, is_active=True).first()
    if not user:
        print("❌ No admin users found")
        return
    
    # Use the test client to simulate admin access
    client.force_login(user)
    response = client.get('/admin/')
    
    if response.status_code == 200:
        print(f"✅ Admin backend working for {user.email}")
        print("💡 Issue is with HTTP session handling, not Django admin")
        print("\n🌐 WORKAROUNDS:")
        print("1. Use production admin: https://admin.bunklogs.net/admin/")
        print("2. Use Django shell for admin tasks:")
        print("   podman exec -it bunk_logs_local_django python manage.py shell")
        print("3. Use management commands for common tasks")
    else:
        print(f"❌ Admin backend not working: {response.status_code}")

def django_shell():
    """Launch Django shell"""
    print("🐍 LAUNCHING DJANGO SHELL:")
    print("-" * 40)
    print("💡 You can now use Django admin functions directly:")
    print("   from django.contrib.auth import get_user_model")
    print("   User = get_user_model()")
    print("   users = User.objects.all()")
    print("")
    os.system("python manage.py shell")

def show_help():
    """Show help"""
    print("🛠️  LOCAL DEVELOPMENT ADMIN HELPER")
    print("=" * 50)
    print("Commands:")
    print("  users     - List all admin users")
    print("  create    - Create new admin user")
    print("  test      - Test admin functionality")
    print("  shell     - Launch Django shell")
    print("  migrate   - Run database migrations")
    print("  help      - Show this help")
    print("")
    print("🌐 Browser Access (if working):")
    print("   http://localhost:8000/admin/")
    print("")
    print("🔒 Production Admin (always works):")
    print("   https://admin.bunklogs.net/admin/")

def main():
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "users":
        show_users()
    elif command == "create":
        create_user()
    elif command == "test":
        test_admin()
    elif command == "shell":
        django_shell()
    elif command == "migrate":
        execute_from_command_line(['manage.py', 'migrate'])
    elif command == "help":
        show_help()
    else:
        print(f"❌ Unknown command: {command}")
        show_help()

if __name__ == "__main__":
    main()
