#!/usr/bin/env python
"""
Fix legacy unit head and camper care assignments by creating UnitStaffAssignment records.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bunk_logs.settings')
django.setup()

from django.utils import timezone
from bunk_logs.bunks.models import Unit, UnitStaffAssignment

def fix_legacy_assignments():
    """
    Create UnitStaffAssignment records for all existing legacy assignments.
    """
    print("=== FIXING LEGACY ASSIGNMENTS ===")
    
    fixed_count = 0
    total_units = 0
    
    for unit in Unit.objects.all():
        total_units += 1
        print(f"\nProcessing Unit: {unit.name}")
        
        # Fix unit_head assignment
        if unit.unit_head:
            existing_assignment = UnitStaffAssignment.objects.filter(
                unit=unit,
                staff_member=unit.unit_head,
                role='unit_head'
            ).first()
            
            if not existing_assignment:
                UnitStaffAssignment.objects.create(
                    unit=unit,
                    staff_member=unit.unit_head,
                    role='unit_head',
                    is_primary=True,
                    start_date=timezone.now().date()
                )
                print(f"  ✅ Created unit_head assignment: {unit.unit_head.email}")
                fixed_count += 1
            else:
                # Update to primary if not already
                if not existing_assignment.is_primary:
                    existing_assignment.is_primary = True
                    existing_assignment.save()
                    print(f"  ✅ Updated unit_head assignment to primary: {unit.unit_head.email}")
                    fixed_count += 1
                else:
                    print(f"  ℹ️ Unit_head assignment already exists: {unit.unit_head.email}")
        
        # Fix camper_care assignment
        if unit.camper_care:
            existing_assignment = UnitStaffAssignment.objects.filter(
                unit=unit,
                staff_member=unit.camper_care,
                role='camper_care'
            ).first()
            
            if not existing_assignment:
                UnitStaffAssignment.objects.create(
                    unit=unit,
                    staff_member=unit.camper_care,
                    role='camper_care',
                    is_primary=True,
                    start_date=timezone.now().date()
                )
                print(f"  ✅ Created camper_care assignment: {unit.camper_care.email}")
                fixed_count += 1
            else:
                # Update to primary if not already
                if not existing_assignment.is_primary:
                    existing_assignment.is_primary = True
                    existing_assignment.save()
                    print(f"  ✅ Updated camper_care assignment to primary: {unit.camper_care.email}")
                    fixed_count += 1
                else:
                    print(f"  ℹ️ Camper_care assignment already exists: {unit.camper_care.email}")
    
    print(f"\n=== SUMMARY ===")
    print(f"Total units processed: {total_units}")
    print(f"Assignments fixed/created: {fixed_count}")
    
    # Show final state
    print(f"\n=== FINAL STATE ===")
    assignments = UnitStaffAssignment.objects.all().order_by('unit__name', 'role')
    for assignment in assignments:
        print(f"{assignment.unit.name} - {assignment.staff_member.email} ({assignment.get_role_display()}) - Primary: {assignment.is_primary}")

if __name__ == "__main__":
    fix_legacy_assignments()
