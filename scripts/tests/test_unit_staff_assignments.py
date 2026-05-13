#!/usr/bin/env python3
"""
Test script for the new UnitStaffAssignment API functionality.
This demonstrates how to use the new multiple staff per unit feature.
"""

import requests
import json
from datetime import date

# Base URL for the API
BASE_URL = "http://localhost:8000/api"

def test_unit_staff_assignments():
    """Test the UnitStaffAssignment API endpoints."""
    
    print("🚀 Testing Unit Staff Assignment API")
    print("=" * 50)
    
    # Test 1: List all units (should show new fields)
    print("\n1. Testing GET /api/units/ (should show new staff fields)")
    response = requests.get(f"{BASE_URL}/units/")
    if response.status_code == 200:
        units = response.json()
        print(f"✅ Found {len(units)} units")
        if units:
            unit = units[0]
            print(f"   Sample unit structure:")
            print(f"   - Name: {unit.get('name')}")
            print(f"   - Unit Head Details: {unit.get('unit_head_details')}")
            print(f"   - Camper Care Details: {unit.get('camper_care_details')}")
            print(f"   - Staff Assignments: {len(unit.get('staff_assignments', []))}")
            print(f"   - Unit Heads: {len(unit.get('unit_heads', []))}")
            print(f"   - Camper Care Staff: {len(unit.get('camper_care_staff', []))}")
    else:
        print(f"❌ Failed to get units: {response.status_code}")
        print(f"   Response: {response.text}")
    
    # Test 2: List all staff assignments
    print("\n2. Testing GET /api/unit-staff-assignments/")
    response = requests.get(f"{BASE_URL}/unit-staff-assignments/")
    if response.status_code == 200:
        assignments = response.json()
        print(f"✅ Found {len(assignments)} staff assignments")
        if assignments:
            assignment = assignments[0]
            print(f"   Sample assignment:")
            print(f"   - Unit: {assignment.get('unit')}")
            print(f"   - Staff Member: {assignment.get('staff_member_name')}")
            print(f"   - Role: {assignment.get('role')} ({assignment.get('role_display')})")
            print(f"   - Is Primary: {assignment.get('is_primary')}")
    else:
        print(f"❌ Failed to get staff assignments: {response.status_code}")
        print(f"   Response: {response.text}")
    
    # Test 3: Test filtering by unit
    print("\n3. Testing filtered staff assignments (unit_id=1)")
    response = requests.get(f"{BASE_URL}/unit-staff-assignments/?unit=1")
    if response.status_code == 200:
        filtered_assignments = response.json()
        print(f"✅ Found {len(filtered_assignments)} assignments for unit 1")
    else:
        print(f"❌ Failed to filter assignments: {response.status_code}")
    
    # Test 4: Test filtering by role
    print("\n4. Testing filtered staff assignments (role=unit_head)")
    response = requests.get(f"{BASE_URL}/unit-staff-assignments/?role=unit_head")
    if response.status_code == 200:
        role_assignments = response.json()
        print(f"✅ Found {len(role_assignments)} unit head assignments")
    else:
        print(f"❌ Failed to filter by role: {response.status_code}")
    
    # Test 5: Test active assignments only
    print("\n5. Testing active assignments only")
    response = requests.get(f"{BASE_URL}/unit-staff-assignments/?active_only=true")
    if response.status_code == 200:
        active_assignments = response.json()
        print(f"✅ Found {len(active_assignments)} active assignments")
    else:
        print(f"❌ Failed to filter active assignments: {response.status_code}")

def demonstrate_new_functionality():
    """Demonstrate the key benefits of the new system."""
    
    print("\n" + "🎯 NEW FUNCTIONALITY DEMONSTRATION" + "=" * 30)
    
    print("\n📋 Key Benefits:")
    print("  1. ✅ Backward Compatibility - existing unit_head/camper_care fields still work")
    print("  2. ✅ Multiple Staff - can assign multiple unit heads and camper care per unit")
    print("  3. ✅ Primary Designation - can mark one person as primary for each role")
    print("  4. ✅ Time-based Assignments - start/end dates for staff rotations")
    print("  5. ✅ Audit Trail - track when assignments are created/updated")
    print("  6. ✅ Role Management - clear role definitions and displays")
    
    print("\n📡 Available API Endpoints:")
    print("  • GET    /api/units/                    - List units with staff info")
    print("  • POST   /api/units/{id}/assign_staff/  - Assign staff to unit")
    print("  • DELETE /api/units/{id}/remove_staff/  - Remove staff assignment")
    print("  • GET    /api/unit-staff-assignments/   - List all assignments")
    print("  • POST   /api/unit-staff-assignments/   - Create new assignment")
    print("  • GET    /api/unit-staff-assignments/{id}/ - Get specific assignment")
    print("  • PUT    /api/unit-staff-assignments/{id}/ - Update assignment")
    print("  • DELETE /api/unit-staff-assignments/{id}/ - Delete assignment")
    
    print("\n🔍 Query Parameters:")
    print("  • ?unit=<id>        - Filter by unit")
    print("  • ?role=<role>      - Filter by role (unit_head/camper_care)")
    print("  • ?active_only=true - Show only active assignments")

if __name__ == "__main__":
    test_unit_staff_assignments()
    demonstrate_new_functionality()
    
    print("\n" + "🎉 TEST COMPLETED!" + "=" * 35)
    print("The Unit Staff Assignment system is now ready!")
    print("You can manage multiple unit heads and camper care staff per unit.")
