#!/usr/bin/env python
"""
Example script demonstrating the test data management system.

This script shows how to:
1. Create test data programmatically
2. Query test data
3. Clean up test data

Run this script with: python manage.py shell < example_test_data.py
"""

print("=== Test Data Management Example ===\n")

# Import required models
from django.contrib.auth import get_user_model
from bunk_logs.campers.models import Camper
from bunk_logs.bunks.models import Cabin, Session, Unit, Bunk

User = get_user_model()

print("1. Creating test data...")

# Create test users
test_user1 = User.objects.create(
    email='test.counselor@example.com',
    first_name='Test',
    last_name='Counselor',
    role='Counselor',
    is_test_data=True
)

test_user2 = User.objects.create(
    email='test.unithead@example.com',
    first_name='Test',
    last_name='UnitHead',
    role='Unit Head',
    is_test_data=True
)

print(f"Created test users: {test_user1.email}, {test_user2.email}")

# Create test cabin
test_cabin = Cabin.objects.create(
    name='Test Cabin A',
    capacity=8,
    location='Test Area',
    is_test_data=True
)

print(f"Created test cabin: {test_cabin.name}")

# Create test session
test_session = Session.objects.create(
    name='Test Session 2025',
    start_date='2025-07-01',
    end_date='2025-08-15',
    is_active=True,
    is_test_data=True
)

print(f"Created test session: {test_session.name}")

# Create test unit
test_unit = Unit.objects.create(
    name='Test Unit Alpha',
    unit_head=test_user2,
    is_test_data=True
)

print(f"Created test unit: {test_unit.name}")

# Create test bunk
test_bunk = Bunk.objects.create(
    cabin=test_cabin,
    session=test_session,
    unit=test_unit,
    is_active=True,
    is_test_data=True
)
test_bunk.counselors.add(test_user1)

print(f"Created test bunk: {test_bunk.name}")

# Create test campers
test_camper1 = Camper.objects.create(
    first_name='Test',
    last_name='Camper One',
    date_of_birth='2012-03-15',
    emergency_contact_name='Test Parent One',
    emergency_contact_phone='555-0001',
    is_test_data=True
)

test_camper2 = Camper.objects.create(
    first_name='Test',
    last_name='Camper Two',
    date_of_birth='2013-05-20',
    emergency_contact_name='Test Parent Two',
    emergency_contact_phone='555-0002',
    is_test_data=True
)

print(f"Created test campers: {test_camper1.full_name}, {test_camper2.full_name}")

print("\n2. Querying test data...")

# Count test data
test_user_count = User.get_test_data_queryset().count()
test_camper_count = Camper.get_test_data_queryset().count()
test_cabin_count = Cabin.get_test_data_queryset().count()
test_session_count = Session.get_test_data_queryset().count()
test_unit_count = Unit.get_test_data_queryset().count()
test_bunk_count = Bunk.get_test_data_queryset().count()

print(f"Test Users: {test_user_count}")
print(f"Test Campers: {test_camper_count}")
print(f"Test Cabins: {test_cabin_count}")
print(f"Test Sessions: {test_session_count}")
print(f"Test Units: {test_unit_count}")
print(f"Test Bunks: {test_bunk_count}")

total_test_records = (test_user_count + test_camper_count + test_cabin_count + 
                     test_session_count + test_unit_count + test_bunk_count)
print(f"\nTotal test records created: {total_test_records}")

print("\n3. Test data is now in the database!")
print("You can now:")
print("- View it in the Django admin with the test data filters")
print("- Run 'python manage.py cleanup_test_data' to see what would be deleted")
print("- Run 'python manage.py cleanup_test_data --confirm' to actually delete it")

print("\n=== Example Complete ===")
print("Run 'python manage.py cleanup_test_data' to see the test data!")
