# Generated by Django 4.2.16 on 2025-06-26 15:35

from django.db import migrations
from django.utils import timezone


def migrate_legacy_staff_assignments(apps, schema_editor):
    """
    Migrate existing unit_head and camper_care assignments from Unit model
    to UnitStaffAssignment model.
    """
    Unit = apps.get_model('bunks', 'Unit')
    UnitStaffAssignment = apps.get_model('bunks', 'UnitStaffAssignment')
    
    for unit in Unit.objects.all():
        # Migrate unit_head if it exists and not already in UnitStaffAssignment
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
        
        # Migrate camper_care if it exists and not already in UnitStaffAssignment
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


def reverse_migrate_legacy_staff_assignments(apps, schema_editor):
    """
    Reverse migration: Move primary UnitStaffAssignment back to Unit fields.
    """
    Unit = apps.get_model('bunks', 'Unit')
    UnitStaffAssignment = apps.get_model('bunks', 'UnitStaffAssignment')
    
    for unit in Unit.objects.all():
        # Find primary unit head assignment
        unit_head_assignment = UnitStaffAssignment.objects.filter(
            unit=unit,
            role='unit_head',
            is_primary=True,
            end_date__isnull=True
        ).first()
        
        if unit_head_assignment and not unit.unit_head:
            unit.unit_head = unit_head_assignment.staff_member
        
        # Find primary camper care assignment
        camper_care_assignment = UnitStaffAssignment.objects.filter(
            unit=unit,
            role='camper_care',
            is_primary=True,
            end_date__isnull=True
        ).first()
        
        if camper_care_assignment and not unit.camper_care:
            unit.camper_care = camper_care_assignment.staff_member
        
        unit.save()


class Migration(migrations.Migration):

    dependencies = [
        ('bunks', '0007_bunk_is_test_data_cabin_is_test_data_and_more'),
    ]

    operations = [
        migrations.RunPython(
            migrate_legacy_staff_assignments,
            reverse_migrate_legacy_staff_assignments
        ),
    ]
