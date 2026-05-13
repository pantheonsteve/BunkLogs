#!/usr/bin/env python3
"""
Test script to verify the legacy staff assignment migration.
"""

import os
import sys
import django

# Add the project directory to Python path
sys.path.insert(0, '/app')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from bunk_logs.bunks.models import Unit, UnitStaffAssignment
from bunk_logs.users.models import User

def test_migration():
    print("=== TESTING STAFF ASSIGNMENT MIGRATION ===\n")
    
    # Get all units
    units = Unit.objects.all()
    print(f"Found {units.count()} units\n")
    
    for unit in units:
        print(f"Unit: {unit.name}")
        
        # Check legacy fields
        legacy_unit_head = unit.unit_head
        legacy_camper_care = unit.camper_care
        
        print(f"  Legacy unit_head: {legacy_unit_head}")
        print(f"  Legacy camper_care: {legacy_camper_care}")
        
        # Check staff assignments
        unit_head_assignments = unit.staff_assignments.filter(role='unit_head')
        camper_care_assignments = unit.staff_assignments.filter(role='camper_care')
        
        print(f"  Unit Head assignments: {unit_head_assignments.count()}")
        for assignment in unit_head_assignments:
            print(f"    - {assignment.staff_member} (Primary: {assignment.is_primary})")
        
        print(f"  Camper Care assignments: {camper_care_assignments.count()}")
        for assignment in camper_care_assignments:
            print(f"    - {assignment.staff_member} (Primary: {assignment.is_primary})")
        
        # Test properties
        primary_unit_head = unit.primary_unit_head
        primary_camper_care = unit.primary_camper_care
        all_unit_heads = unit.all_unit_heads
        all_camper_care = unit.all_camper_care
        
        print(f"  Primary unit head (via property): {primary_unit_head}")
        print(f"  Primary camper care (via property): {primary_camper_care}")
        print(f"  All unit heads: {[str(u) for u in all_unit_heads]}")
        print(f"  All camper care: {[str(u) for u in all_camper_care]}")
        
        # Verify migration was successful
        migration_issues = []
        
        if legacy_unit_head:
            # Check if legacy unit head is represented in staff assignments
            has_assignment = unit_head_assignments.filter(staff_member=legacy_unit_head).exists()
            if not has_assignment:
                migration_issues.append(f"Legacy unit head {legacy_unit_head} not found in staff assignments")
            elif legacy_unit_head not in all_unit_heads:
                migration_issues.append(f"Legacy unit head {legacy_unit_head} not in all_unit_heads property")
        
        if legacy_camper_care:
            # Check if legacy camper care is represented in staff assignments
            has_assignment = camper_care_assignments.filter(staff_member=legacy_camper_care).exists()
            if not has_assignment:
                migration_issues.append(f"Legacy camper care {legacy_camper_care} not found in staff assignments")
            elif legacy_camper_care not in all_camper_care:
                migration_issues.append(f"Legacy camper care {legacy_camper_care} not in all_camper_care property")
        
        if migration_issues:
            print(f"  ❌ MIGRATION ISSUES:")
            for issue in migration_issues:
                print(f"    - {issue}")
        else:
            print(f"  ✅ Migration successful")
        
        print()
    
    # Overall summary
    print("=== MIGRATION SUMMARY ===")
    total_assignments = UnitStaffAssignment.objects.count()
    unit_head_assignments_total = UnitStaffAssignment.objects.filter(role='unit_head').count()
    camper_care_assignments_total = UnitStaffAssignment.objects.filter(role='camper_care').count()
    primary_assignments = UnitStaffAssignment.objects.filter(is_primary=True).count()
    
    print(f"Total staff assignments: {total_assignments}")
    print(f"Unit head assignments: {unit_head_assignments_total}")
    print(f"Camper care assignments: {camper_care_assignments_total}")
    print(f"Primary assignments: {primary_assignments}")
    
    # Check for units with legacy assignments but no staff assignments
    units_with_legacy_but_no_assignments = 0
    for unit in units:
        has_legacy = unit.unit_head or unit.camper_care
        has_assignments = unit.staff_assignments.exists()
        if has_legacy and not has_assignments:
            units_with_legacy_but_no_assignments += 1
            print(f"❌ Unit {unit.name} has legacy assignments but no staff assignments")
    
    if units_with_legacy_but_no_assignments == 0:
        print("✅ All units with legacy assignments have corresponding staff assignments")
    
    print("\n=== TESTING API BEHAVIOR ===")
    # Test that the API properties work correctly
    for unit in units:
        if unit.staff_assignments.exists() or unit.unit_head or unit.camper_care:
            print(f"Unit: {unit.name}")
            print(f"  API will return primary_unit_head: {unit.primary_unit_head}")
            print(f"  API will return primary_camper_care: {unit.primary_camper_care}")
            print()

if __name__ == "__main__":
    test_migration()
