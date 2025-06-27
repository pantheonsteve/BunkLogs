#!/usr/bin/env python
"""
Update all API views to remove legacy unit_head and camper_care field references.
"""

import re

def update_api_views():
    views_file = "/app/bunk_logs/api/views.py"
    
    with open(views_file, 'r') as f:
        content = f.read()
    
    print("=== UPDATING API VIEWS ===")
    
    # Pattern 1: Remove legacy approach sections for Unit Head
    pattern1 = r'# Legacy approach\s*\n\s*unit_ids\.extend\(user\.managed_units\.values_list\([^)]+\)\)\s*\n\s*# New approach'
    replacement1 = '# Get units via UnitStaffAssignment'
    content = re.sub(pattern1, replacement1, content)
    print("✅ Removed legacy managed_units approach sections")
    
    # Pattern 2: Remove legacy approach sections for Camper Care
    pattern2 = r'# Legacy approach\s*\n\s*unit_ids\.extend\(user\.camper_care_units\.values_list\([^)]+\)\)\s*\n\s*# New approach'
    replacement2 = '# Get units via UnitStaffAssignment'
    content = re.sub(pattern2, replacement2, content)
    print("✅ Removed legacy camper_care_units approach sections")
    
    # Pattern 3: Remove remaining managed_units references
    pattern3 = r'user\.managed_units\.filter\([^)]+\)\.exists\(\)'
    content = re.sub(pattern3, 'False  # Legacy field removed', content)
    print("✅ Removed remaining managed_units.filter() calls")
    
    # Pattern 4: Remove unit_ids declarations and extend calls
    pattern4 = r'unit_ids = \[\]\s*\n\s*unit_ids\.extend\(unit_assignments\)'
    replacement4 = 'unit_ids = list(unit_assignments)'
    content = re.sub(pattern4, replacement4, content)
    print("✅ Simplified unit_ids assignment")
    
    # Pattern 5: Replace set(unit_ids) with unit_assignments directly where appropriate
    pattern5 = r'unit_id__in=set\(unit_ids\)'
    replacement5 = 'unit_id__in=unit_assignments'
    content = re.sub(pattern5, replacement5, content)
    print("✅ Simplified unit_id__in filters")
    
    # Pattern 6: Fix comments that reference both approaches
    pattern6 = r'# Check both legacy.*? field and new staff assignments'
    replacement6 = '# Check staff assignments'
    content = re.sub(pattern6, replacement6, content)
    print("✅ Updated comments")
    
    # Pattern 7: Remove has_access legacy checks
    pattern7 = r'# Legacy approach\s*\n\s*if user\.managed_units\.filter\([^)]+\)\.exists\(\):\s*\n\s*has_access = True\s*\n\s*# New approach'
    replacement7 = '# Check staff assignments'
    content = re.sub(pattern7, replacement7, content)
    print("✅ Removed legacy has_access checks")
    
    with open(views_file, 'w') as f:
        f.write(content)
    
    print("✅ API views updated successfully!")

if __name__ == "__main__":
    update_api_views()
