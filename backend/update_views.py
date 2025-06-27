#!/usr/bin/env python
"""
Update API views to remove all legacy unit_head and camper_care references
and use only UnitStaffAssignment.
"""
import os
import re

def update_views_file():
    views_file = "/Users/steve.bresnick/Projects/BunkLogs/backend/bunk_logs/api/views.py"
    
    with open(views_file, 'r') as f:
        content = f.read()
    
    # Track changes
    changes = []
    
    # Replace managed_units references
    pattern1 = r'user\.managed_units\.values_list\([^)]+\)'
    if re.search(pattern1, content):
        changes.append("Removed user.managed_units references")
        content = re.sub(pattern1, '', content)
    
    # Replace camper_care_units references
    pattern2 = r'user\.camper_care_units\.values_list\([^)]+\)'
    if re.search(pattern2, content):
        changes.append("Removed user.camper_care_units references")
        content = re.sub(pattern2, '', content)
    
    # Fix the patterns that create empty unit_ids.extend() calls
    content = re.sub(r'unit_ids\.extend\(\s*\)', '', content)
    
    # Fix duplicate legacy approach comments and empty sections
    content = re.sub(r'\s*# Legacy approach\s*\n\s*# New approach', '\n            # Get units via UnitStaffAssignment', content)
    
    # Clean up multiple empty lines
    content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
    
    # Update specific patterns for unit head and camper care filtering
    # Pattern for unit head filtering
    unit_head_pattern = r'if user\.role == \'Unit Head\':\s*.*?unit_ids = \[\].*?unit_ids\.extend.*?\n.*?# New approach.*?unit_assignments = UnitStaffAssignment\.objects\.filter.*?\.values_list\(\'unit_id\', flat=True\).*?unit_ids\.extend\(unit_assignments\).*?return.*?bunk_assignment__bunk__unit_id__in=set\(unit_ids\)'
    
    # This is complex, let me write specific replacements for each section
    
    with open(views_file, 'w') as f:
        f.write(content)
    
    return changes

if __name__ == "__main__":
    changes = update_views_file()
    print("Changes made:")
    for change in changes:
        print(f"- {change}")
