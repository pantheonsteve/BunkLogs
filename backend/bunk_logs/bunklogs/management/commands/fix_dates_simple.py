from django.core.management.base import BaseCommand
from django.utils import timezone
from bunk_logs.bunklogs.models import BunkLog, CounselorLog


class Command(BaseCommand):
    help = "Fix date fields to match the date from created_at field"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be changed without making changes",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        
        if dry_run:
            self.stdout.write("🔍 DRY RUN - No changes will be made")
        
        self.stdout.write("🔧 Fixing BunkLog dates...")
        bunk_fixed = self.fix_bunk_logs(dry_run)
        
        self.stdout.write("🔧 Fixing CounselorLog dates...")
        counselor_fixed = self.fix_counselor_logs(dry_run)
        
        action = "Would fix" if dry_run else "Fixed"
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ {action} {bunk_fixed} BunkLog records and {counselor_fixed} CounselorLog records"
            )
        )

    def fix_bunk_logs(self, dry_run=False):
        """Fix BunkLog date fields to match created_at date."""
        fixed_count = 0
        skipped_count = 0
        
        for log in BunkLog.objects.all():
            # Convert created_at to local timezone and get the date
            created_date = timezone.localtime(log.created_at).date()
            
            # Check if date field doesn't match created_at date
            if log.date != created_date:
                # Check if updating would create a duplicate
                existing = BunkLog.objects.filter(
                    bunk_assignment_id=log.bunk_assignment_id,
                    date=created_date
                ).exclude(id=log.id).exists()
                
                if existing:
                    if dry_run:
                        self.stdout.write(
                            f"  Would SKIP BunkLog ID {log.id}: {log.date} → {created_date} (would create duplicate)"
                        )
                    else:
                        self.stdout.write(
                            f"  SKIPPED BunkLog ID {log.id}: would create duplicate with date {created_date}"
                        )
                    skipped_count += 1
                else:
                    if dry_run:
                        self.stdout.write(
                            f"  Would fix BunkLog ID {log.id}: {log.date} → {created_date}"
                        )
                    else:
                        # Use direct update to avoid unique constraint issues
                        BunkLog.objects.filter(id=log.id).update(date=created_date)
                        self.stdout.write(
                            f"  Fixed BunkLog ID {log.id}: date updated to {created_date}"
                        )
                    fixed_count += 1
        
        if skipped_count > 0:
            self.stdout.write(f"  Skipped {skipped_count} records that would create duplicates")
        
        return fixed_count

    def fix_counselor_logs(self, dry_run=False):
        """Fix CounselorLog date fields to match created_at date."""
        fixed_count = 0
        skipped_count = 0
        
        for log in CounselorLog.objects.all():
            # Convert created_at to local timezone and get the date
            created_date = timezone.localtime(log.created_at).date()
            
            # Check if date field doesn't match created_at date
            if log.date != created_date:
                # Check if updating would create a duplicate
                existing = CounselorLog.objects.filter(
                    counselor_id=log.counselor_id,
                    date=created_date
                ).exclude(id=log.id).exists()
                
                if existing:
                    if dry_run:
                        self.stdout.write(
                            f"  Would SKIP CounselorLog ID {log.id}: {log.date} → {created_date} (would create duplicate)"
                        )
                    else:
                        self.stdout.write(
                            f"  SKIPPED CounselorLog ID {log.id}: would create duplicate with date {created_date}"
                        )
                    skipped_count += 1
                else:
                    if dry_run:
                        self.stdout.write(
                            f"  Would fix CounselorLog ID {log.id}: {log.date} → {created_date}"
                        )
                    else:
                        # Use direct update to avoid unique constraint issues
                        CounselorLog.objects.filter(id=log.id).update(date=created_date)
                        self.stdout.write(
                            f"  Fixed CounselorLog ID {log.id}: date updated to {created_date}"
                        )
                    fixed_count += 1
        
        if skipped_count > 0:
            self.stdout.write(f"  Skipped {skipped_count} records that would create duplicates")
        
        return fixed_count
