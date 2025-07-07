from django.core.management.base import BaseCommand
from bunk_logs.bunklogs.models import BunkLog
from django.db.models import Count


class Command(BaseCommand):
    help = 'Check for duplicate BunkLog records'

    def handle(self, *args, **options):
        # Find duplicates by bunk_assignment_id and date
        duplicates = BunkLog.objects.values('bunk_assignment_id', 'date').annotate(
            count=Count('id')
        ).filter(count__gt=1).order_by('-count')

        self.stdout.write(f'Found {duplicates.count()} sets of duplicate records:\n')
        
        for i, dup in enumerate(duplicates[:10]):
            self.stdout.write(f'{i+1}. bunk_assignment_id={dup["bunk_assignment_id"]}, date={dup["date"]}, count={dup["count"]}')
            
            # Get details for this duplicate set
            records = BunkLog.objects.filter(
                bunk_assignment_id=dup['bunk_assignment_id'], 
                date=dup['date']
            ).order_by('created_at')
            
            for record in records:
                has_data = any([record.present is not None, record.behavior, record.notes])
                self.stdout.write(f'   ID={record.id}, created={record.created_at.strftime("%Y-%m-%d %H:%M")}, has_data={has_data}')
                if record.notes:
                    notes_preview = record.notes[:50] + '...' if len(record.notes) > 50 else record.notes
                    self.stdout.write(f'     notes: {notes_preview}')
            self.stdout.write('')
