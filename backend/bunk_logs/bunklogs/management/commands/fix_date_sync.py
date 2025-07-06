from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from bunk_logs.bunklogs.models import BunkLog, CounselorLog


class Command(BaseCommand):
    help = 'Fix BunkLog and CounselorLog records with mismatched date and created_at fields'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of records to process in each batch (default: 100)',
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit the number of records to fix (for testing)',
        )
        parser.add_argument(
            '--bunklogs-only',
            action='store_true',
            help='Only fix BunkLog records, skip CounselorLog records',
        )
        parser.add_argument(
            '--counselorlogs-only',
            action='store_true',
            help='Only fix CounselorLog records, skip BunkLog records',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        batch_size = options['batch_size']
        limit = options['limit']
        bunklogs_only = options['bunklogs_only']
        counselorlogs_only = options['counselorlogs_only']
        
        mode = "DRY RUN" if dry_run else "LIVE"
        self.stdout.write(self.style.WARNING(f"🔧 Starting date sync fix - {mode} MODE"))
        self.stdout.write("=" * 80)
        
        if bunklogs_only and counselorlogs_only:
            self.stdout.write(self.style.ERROR("Cannot use both --bunklogs-only and --counselorlogs-only"))
            return
        
        # Process BunkLogs
        if not counselorlogs_only:
            self.fix_bunklogs(dry_run, batch_size, limit)
        
        # Process CounselorLogs
        if not bunklogs_only:
            self.fix_counselorlogs(dry_run, batch_size, limit)
        
        if dry_run:
            self.stdout.write(self.style.WARNING("\n⚠️  This was a DRY RUN - no changes were made"))
            self.stdout.write("To apply changes, run without --dry-run flag")
        else:
            self.stdout.write(self.style.SUCCESS("\n✅ Date sync fix completed!"))
            self.stdout.write("\n💡 Run 'python manage.py check_date_sync' to verify the fixes.")

    def fix_bunklogs(self, dry_run, batch_size, limit):
        self.stdout.write(self.style.SUCCESS("\n📋 Processing BunkLog records..."))
        
        # Find records that need updating
        mismatched_logs = []
        processed = 0
        
        for log in BunkLog.objects.all().order_by('id'):
            if limit and len(mismatched_logs) >= limit:
                break
                
            created_date = timezone.localtime(log.created_at).date()
            if log.date != created_date:
                try:
                    camper_name = f"{log.bunk_assignment.camper.first_name} {log.bunk_assignment.camper.last_name}"
                except:
                    camper_name = "Unknown"
                    
                mismatched_logs.append({
                    'log': log,
                    'camper_name': camper_name,
                    'id': log.id,
                    'old_date': log.date,
                    'new_date': created_date,
                    'description': log.description[:100] + '...' if len(log.description) > 100 else log.description
                })
            
            processed += 1
            if processed % 1000 == 0:
                self.stdout.write(f"Scanned {processed} BunkLog records...")
        
        self.stdout.write(f"Found {len(mismatched_logs)} BunkLog records to fix")
        
        if not mismatched_logs:
            self.stdout.write("✅ No BunkLog records need fixing")
            return
        
        # Show examples
        self.stdout.write("\n📊 Examples of changes:")
        for i, item in enumerate(mismatched_logs[:5]):
            self.stdout.write(f"  ID {item['id']}: {item['camper_name']} - {item['old_date']} → {item['new_date']}")
            self.stdout.write(f"    Description: {item['description'] or 'No description'}")
        
        if len(mismatched_logs) > 5:
            self.stdout.write(f"  ... and {len(mismatched_logs) - 5} more")
        
        if dry_run:
            return
        
        # Apply fixes in batches
        self.stdout.write(f"\n🔧 Applying fixes in batches of {batch_size}...")
        
        fixed_count = 0
        for i in range(0, len(mismatched_logs), batch_size):
            batch = mismatched_logs[i:i + batch_size]
            
            with transaction.atomic():
                for item in batch:
                    try:
                        # Use queryset update to avoid triggering our new save method
                        BunkLog.objects.filter(pk=item['id']).update(date=item['new_date'])
                        fixed_count += 1
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"Error fixing BunkLog ID {item['id']}: {e}")
                        )
            
            self.stdout.write(f"Fixed batch {i//batch_size + 1}: {len(batch)} records")
        
        self.stdout.write(self.style.SUCCESS(f"✅ Fixed {fixed_count} BunkLog records"))

    def fix_counselorlogs(self, dry_run, batch_size, limit):
        self.stdout.write(self.style.SUCCESS("\n📋 Processing CounselorLog records..."))
        
        # Find records that need updating
        mismatched_logs = []
        processed = 0
        
        for log in CounselorLog.objects.all().order_by('id'):
            if limit and len(mismatched_logs) >= limit:
                break
                
            created_date = timezone.localtime(log.created_at).date()
            if log.date != created_date:
                try:
                    counselor_name = log.counselor.get_full_name() if hasattr(log.counselor, 'get_full_name') else str(log.counselor)
                except:
                    counselor_name = "Unknown"
                    
                mismatched_logs.append({
                    'log': log,
                    'counselor_name': counselor_name,
                    'id': log.id,
                    'old_date': log.date,
                    'new_date': created_date,
                    'elaboration': log.elaboration[:100] + '...' if len(log.elaboration) > 100 else log.elaboration
                })
            
            processed += 1
            if processed % 1000 == 0:
                self.stdout.write(f"Scanned {processed} CounselorLog records...")
        
        self.stdout.write(f"Found {len(mismatched_logs)} CounselorLog records to fix")
        
        if not mismatched_logs:
            self.stdout.write("✅ No CounselorLog records need fixing")
            return
        
        # Show examples
        self.stdout.write("\n📊 Examples of changes:")
        for i, item in enumerate(mismatched_logs[:5]):
            self.stdout.write(f"  ID {item['id']}: {item['counselor_name']} - {item['old_date']} → {item['new_date']}")
            self.stdout.write(f"    Elaboration: {item['elaboration'] or 'No elaboration'}")
        
        if len(mismatched_logs) > 5:
            self.stdout.write(f"  ... and {len(mismatched_logs) - 5} more")
        
        if dry_run:
            return
        
        # Apply fixes in batches
        self.stdout.write(f"\n🔧 Applying fixes in batches of {batch_size}...")
        
        fixed_count = 0
        for i in range(0, len(mismatched_logs), batch_size):
            batch = mismatched_logs[i:i + batch_size]
            
            with transaction.atomic():
                for item in batch:
                    try:
                        # Use queryset update to avoid triggering our new save method
                        CounselorLog.objects.filter(pk=item['id']).update(date=item['new_date'])
                        fixed_count += 1
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"Error fixing CounselorLog ID {item['id']}: {e}")
                        )
            
            self.stdout.write(f"Fixed batch {i//batch_size + 1}: {len(batch)} records")
        
        self.stdout.write(self.style.SUCCESS(f"✅ Fixed {fixed_count} CounselorLog records"))
