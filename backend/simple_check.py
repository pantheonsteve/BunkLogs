from bunklogs.models import BunkLog
from django.db.models import Count

duplicates = BunkLog.objects.values('bunk_assignment_id', 'date').annotate(count=Count('id')).filter(count__gt=1).order_by('-count')

print('Found', duplicates.count(), 'sets of duplicate records')

for i, dup in enumerate(duplicates[:5]):
    print(f'{i+1}. bunk_assignment={dup["bunk_assignment_id"]}, date={dup["date"]}, count={dup["count"]}')
    
    records = BunkLog.objects.filter(bunk_assignment_id=dup["bunk_assignment_id"], date=dup["date"]).order_by('created_at')
    
    for record in records:
        has_data = any([record.present is not None, record.behavior, record.notes])
        print(f'   ID={record.id}, created={record.created_at}, has_data={has_data}')
