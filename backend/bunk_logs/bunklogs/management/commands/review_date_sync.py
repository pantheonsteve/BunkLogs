from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from bunk_logs.bunklogs.models import BunkLog, CounselorLog


class Command(BaseCommand):
    help = 'Fix date sync with detailed descriptions for review'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )
        parser.add_argument(
            '--show-descriptions',
            action='store_true',
            help='Show record descriptions for review',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        show_descriptions = options['show_descriptions']
        
        mode = "DRY RUN" if dry_run else "LIVE"
        self.stdout.write(f"🔧 Starting detailed date sync review - {mode} MODE")
        self.stdout.write("=" * 80)
        
        # Process BunkLogs
        self.stdout.write("\n📋 Processing BunkLog records...")
        
        # Find records that need updating
        mismatched_logs = []
        
        for log in BunkLog.objects.all().order_by('id'):
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
                    'description': log.description
                })
        
        self.stdout.write(f"Found {len(mismatched_logs)} BunkLog records to fix")
        
        if mismatched_logs:
            self.stdout.write("\n📊 First 10 records with descriptions:")
            for i, item in enumerate(mismatched_logs[:10]):
                self.stdout.write(f"  ID {item['id']}: {item['camper_name']}")
                self.stdout.write(f"    Date: {item['old_date']} → {item['new_date']}")
                if show_descriptions:
                    desc = item['description'][:100] + ('...' if len(item['description']) > 100 else '')
                    self.stdout.write(f"    Description: '{desc}'")
                self.stdout.write("")
        
        # Process CounselorLogs
        self.stdout.write("\n📋 Processing CounselorLog records...")
        
        mismatched_counselor_logs = []
        
        for log in CounselorLog.objects.all().order_by('id'):
            created_date = timezone.localtime(log.created_at).date()
            if log.date != created_date:
                try:
                    counselor_name = log.counselor.get_full_name()
                except:
                    counselor_name = "Unknown"
                    
                mismatched_counselor_logs.append({
                    'log': log,
                    'counselor_name': counselor_name,
                    'id': log.id,
                    'old_date': log.date,
                    'new_date': created_date,
                    'elaboration': log.elaboration
                })
        
        self.stdout.write(f"Found {len(mismatched_counselor_logs)} CounselorLog records to fix")
        
        if mismatched_counselor_logs:
            self.stdout.write("\n📊 CounselorLog records with descriptions:")
            for item in mismatched_counselor_logs:
                self.stdout.write(f"  ID {item['id']}: {item['counselor_name']}")
                self.stdout.write(f"    Date: {item['old_date']} → {item['new_date']}")
                if show_descriptions:
                    desc = item['elaboration'][:100] + ('...' if len(item['elaboration']) > 100 else '')
                    self.stdout.write(f"    Elaboration: '{desc}'")
                self.stdout.write("")
        
        if dry_run:
            self.stdout.write("\n⚠️  This was a DRY RUN - no changes were made")
            self.stdout.write("To apply changes, use the regular fix_date_sync command")
            return
        
        # Apply fixes
        self.stdout.write("\n🔧 Applying fixes...")
        
        fixed_bunk = 0
        for item in mismatched_logs:
            try:
                BunkLog.objects.filter(pk=item['id']).update(date=item['new_date'])
                fixed_bunk += 1
            except Exception as e:
                self.stdout.write(f"Error fixing BunkLog ID {item['id']}: {e}")
        
        fixed_counselor = 0
        for item in mismatched_counselor_logs:
            try:
                CounselorLog.objects.filter(pk=item['id']).update(date=item['new_date'])
                fixed_counselor += 1
            except Exception as e:
                self.stdout.write(f"Error fixing CounselorLog ID {item['id']}: {e}")
        
        self.stdout.write(f"\n✅ Fixed {fixed_bunk} BunkLog records")
        self.stdout.write(f"✅ Fixed {fixed_counselor} CounselorLog records")
