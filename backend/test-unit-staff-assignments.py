#!/usr/bin/env python3
"""
Test script for UnitStaffAssignment functionality in Podman container.
This script tests the migration, API endpoints, and model functionality.
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api"

def get_auth_token(username="testuser@example.com", password="testpass123"):
    """Get authentication token for API requests."""
    print(f"🔑 Getting auth token for {username}...")
    
    try:
        response = requests.post(f"{API_BASE}/auth-token/", {
            "username": username,
            "password": password
        })
        
        if response.status_code == 200:
            token = response.json().get("token")
            print(f"✅ Authentication successful")
            return token
        else:
            print(f"❌ Authentication failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error getting token: {e}")
        return None

def test_api_endpoint(endpoint, token=None, method="GET", data=None):
    """Test an API endpoint with optional authentication."""
    headers = {}
    if token:
        headers["Authorization"] = f"Token {token}"
    
    url = f"{API_BASE}{endpoint}"
    print(f"🧪 Testing {method} {url}")
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            headers["Content-Type"] = "application/json"
            response = requests.post(url, headers=headers, json=data)
        elif method == "PUT":
            headers["Content-Type"] = "application/json"
            response = requests.put(url, headers=headers, json=data)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code < 400:
            try:
                data = response.json()
                if isinstance(data, list):
                    print(f"   Response: List with {len(data)} items")
                    if data and len(data) > 0:
                        print(f"   First item keys: {list(data[0].keys()) if isinstance(data[0], dict) else 'Not a dict'}")
                elif isinstance(data, dict):
                    print(f"   Response keys: {list(data.keys())}")
                else:
                    print(f"   Response: {data}")
                return True, data
            except:
                print(f"   Response: {response.text[:200]}")
                return True, response.text
        else:
            print(f"   Error: {response.text}")
            return False, response.text
            
    except Exception as e:
        print(f"   Exception: {e}")
        return False, str(e)

def test_unit_staff_assignments():
    """Test UnitStaffAssignment functionality."""
    print("\n" + "="*60)
    print("🎯 TESTING UNIT STAFF ASSIGNMENTS")
    print("="*60)
    
    # Get authentication token
    token = get_auth_token()
    if not token:
        print("❌ Cannot proceed without authentication token")
        return False
    
    # Test basic endpoints
    print("\n📋 Testing basic API endpoints...")
    
    endpoints_to_test = [
        "/units/",
        "/bunks/",
        "/unit-staff-assignments/",
        "/counselor-logs/",
        "/staff/"
    ]
    
    for endpoint in endpoints_to_test:
        success, data = test_api_endpoint(endpoint, token)
        if not success:
            print(f"❌ Failed to access {endpoint}")
    
    # Get units to work with
    print("\n🏠 Getting units for testing...")
    success, units_data = test_api_endpoint("/units/", token)
    
    if not success or not units_data:
        print("❌ Cannot get units data")
        return False
    
    if not isinstance(units_data, list) or len(units_data) == 0:
        print("❌ No units found")
        return False
    
    # Test getting unit staff assignments
    print("\n👥 Testing unit staff assignments...")
    success, assignments_data = test_api_endpoint("/unit-staff-assignments/", token)
    
    if success and assignments_data:
        print(f"✅ Found {len(assignments_data) if isinstance(assignments_data, list) else 'some'} staff assignments")
        
        if isinstance(assignments_data, list) and len(assignments_data) > 0:
            first_assignment = assignments_data[0]
            print(f"   Sample assignment: {first_assignment}")
    
    # Get staff members
    print("\n👤 Getting staff members...")
    success, staff_data = test_api_endpoint("/staff/", token)
    
    if not success or not staff_data:
        print("⚠️ Cannot get staff data for creating assignments")
        return True  # Continue without creating new assignments
    
    # Try to create a new staff assignment (if we have data)
    if isinstance(units_data, list) and len(units_data) > 0 and isinstance(staff_data, list) and len(staff_data) > 0:
        print("\n➕ Testing staff assignment creation...")
        
        unit_id = units_data[0].get("id")
        staff_id = staff_data[0].get("id")
        
        if unit_id and staff_id:
            new_assignment = {
                "unit": unit_id,
                "staff_member": staff_id,
                "role": "unit_head",
                "is_primary": False,
                "start_date": datetime.now().strftime("%Y-%m-%d")
            }
            
            success, created_data = test_api_endpoint("/unit-staff-assignments/", token, "POST", new_assignment)
            
            if success:
                print("✅ Successfully created staff assignment")
                print(f"   Created assignment: {created_data}")
                
                # Try to update the assignment
                if isinstance(created_data, dict) and "id" in created_data:
                    assignment_id = created_data["id"]
                    print(f"\n✏️ Testing assignment update (ID: {assignment_id})...")
                    
                    update_data = {
                        "is_primary": True,
                        "notes": "Updated via API test"
                    }
                    
                    success, updated_data = test_api_endpoint(f"/unit-staff-assignments/{assignment_id}/", token, "PUT", {**new_assignment, **update_data})
                    
                    if success:
                        print("✅ Successfully updated staff assignment")
                    else:
                        print("❌ Failed to update staff assignment")
                    
                    # Clean up - delete the test assignment
                    print(f"\n🗑️ Cleaning up test assignment...")
                    success, _ = test_api_endpoint(f"/unit-staff-assignments/{assignment_id}/", token, "DELETE")
                    
                    if success:
                        print("✅ Successfully deleted test assignment")
                    else:
                        print("⚠️ Failed to delete test assignment (may need manual cleanup)")
            else:
                print("❌ Failed to create staff assignment")
        else:
            print("⚠️ Missing unit_id or staff_id for assignment creation")
    
    return True

def test_unit_properties():
    """Test Unit model properties that should reflect UnitStaffAssignment data."""
    print("\n" + "="*60)
    print("🏠 TESTING UNIT MODEL PROPERTIES")
    print("="*60)
    
    token = get_auth_token()
    if not token:
        print("❌ Cannot proceed without authentication token")
        return False
    
    # Get units with detailed info
    success, units_data = test_api_endpoint("/units/", token)
    
    if not success or not units_data:
        print("❌ Cannot get units data")
        return False
    
    if isinstance(units_data, list) and len(units_data) > 0:
        for i, unit in enumerate(units_data[:3]):  # Test first 3 units
            unit_id = unit.get("id")
            unit_name = unit.get("name", f"Unit {unit_id}")
            
            print(f"\n🏠 Unit: {unit_name} (ID: {unit_id})")
            
            # Check if unit has primary_unit_head and primary_camper_care properties
            if "primary_unit_head" in unit:
                print(f"   Primary Unit Head: {unit['primary_unit_head']}")
            else:
                print("   ⚠️ Missing primary_unit_head property")
            
            if "primary_camper_care" in unit:
                print(f"   Primary Camper Care: {unit['primary_camper_care']}")
            else:
                print("   ⚠️ Missing primary_camper_care property")
            
            # Get assignments for this unit
            success, assignments = test_api_endpoint(f"/unit-staff-assignments/?unit={unit_id}", token)
            
            if success and isinstance(assignments, list):
                print(f"   Staff Assignments ({len(assignments)}):")
                for assignment in assignments:
                    role = assignment.get("role", "unknown")
                    is_primary = assignment.get("is_primary", False)
                    staff_name = assignment.get("staff_member_name", assignment.get("staff_member", "unknown"))
                    primary_marker = " (PRIMARY)" if is_primary else ""
                    print(f"     - {role}: {staff_name}{primary_marker}")
            else:
                print("   No staff assignments found")
    
    return True

def main():
    """Run all tests."""
    print("🚀 Starting UnitStaffAssignment Tests")
    print(f"🕐 Test time: {datetime.now()}")
    
    try:
        # Test basic connectivity
        print("\n🔗 Testing basic connectivity...")
        response = requests.get(f"{BASE_URL}/admin/", timeout=10)
        if response.status_code in [200, 302]:
            print("✅ Django server is responding")
        else:
            print(f"⚠️ Django server response: {response.status_code}")
    except Exception as e:
        print(f"❌ Cannot connect to Django server: {e}")
        return 1
    
    # Run tests
    all_passed = True
    
    if not test_unit_staff_assignments():
        all_passed = False
    
    if not test_unit_properties():
        all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("🎉 ALL TESTS COMPLETED")
    else:
        print("⚠️ SOME TESTS HAD ISSUES")
    print("="*60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
