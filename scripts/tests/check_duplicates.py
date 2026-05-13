#!/usr/bin/env python3
"""
Check for duplicate BunkLog records that would cause unique constraint violations.
"""

import os
import sys
import django

# Setup Django
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from bunklogs.models import BunkLog
from django.db.models import Count

def check_duplicates():
    # Find duplicates by bunk_assignment_id and date
    duplicates = BunkLog.objects.values('bunk_assignment_id', 'date').annotate(
        count=Count('id')
    ).filter(count__gt=1).order_by('-count')

    print(f'Found {duplicates.count()} sets of duplicate records:')
    
    for i, dup in enumerate(duplicates[:10]):
        print(f'  {i+1}. bunk_assignment_id={dup["bunk_assignment_id"]}, date={dup["date"]}, count={dup["count"]}')
        
        # Get details for this duplicate set
        records = BunkLog.objects.filter(
            bunk_assignment_id=dup['bunk_assignment_id'], 
            date=dup['date']
        ).order_by('created_at')
        
        print(f'     Records:')
        for record in records:
            has_data = any([record.present is not None, record.behavior, record.notes])
            print(f'       ID={record.id}, created={record.created_at}, has_data={has_data}')
            if record.notes:
                print(f'         notes: {record.notes[:50]}...' if len(record.notes) > 50 else f'         notes: {record.notes}')
        print()

if __name__ == '__main__':
    check_duplicates()
