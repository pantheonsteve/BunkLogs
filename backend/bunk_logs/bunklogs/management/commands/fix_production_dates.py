"""
Django management command to fix production BunkLog date issues.

This command addresses the issue where BunkLogs were created on July 6th but 
incorrectly dated July 7th due to the old date-shifting logic.

Strategy:
1. Find all BunkLogs with date=2025-07-07 but created_at on 2025-07-06
2. For each problematic log, check if there's already a correct log for that camper on 2025-07-06
3. If duplicate exists: DELETE the incorrectly dated July 7th log
4. If no duplicate: UPDATE the date to match the created_at date (2025-07-06)
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import date, datetime
from bunk_logs.bunklogs.models import BunkLog


class Command(BaseCommand):
    help = 'Fix production BunkLog date inconsistencies from July 6-7, 2025'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Actually perform the changes (required for real execution)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        
        if not dry_run and not force:
            self.stdout.write(
                self.style.ERROR(
                    'You must specify either --dry-run or --force. '
                    'Use --dry-run first to see what would be changed.'
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"{'[DRY RUN] ' if dry_run else ''}Analyzing BunkLog date inconsistencies..."
            )
        )

        # Define the problematic dates
        problem_date = date(2025, 7, 7)  # Incorrectly dated logs
        correct_date = date(2025, 7, 6)   # What the date should be
        
        # Find logs that were created on July 6th but dated July 7th
        # We need to check created_at timestamp to see if it was actually created on July 6th
        july_7_logs = BunkLog.objects.filter(date=problem_date)
        
        # Filter to only those created on July 6th (accounting for timezone)
        problematic_logs = []
        for log in july_7_logs:
            # Convert to local timezone and check the date
            local_created = timezone.localtime(log.created_at)
            if local_created.date() == correct_date:
                problematic_logs.append(log)
        
        self.stdout.write(f"Found {len(problematic_logs)} problematic logs (dated 2025-07-07 but created on 2025-07-06)")
        
        if not problematic_logs:
            self.stdout.write(self.style.SUCCESS("No problematic logs found!"))
            return

        # Analyze each problematic log
        logs_to_delete = []
        logs_to_update = []
        
        for log in problematic_logs:
            # Check if there's already a correct log for this camper on July 6th
            existing_correct_log = BunkLog.objects.filter(
                bunk_assignment=log.bunk_assignment,
                date=correct_date
            ).exclude(id=log.id).first()
            
            if existing_correct_log:
                # Duplicate exists - mark for deletion
                logs_to_delete.append({
                    'log': log,
                    'reason': f'Duplicate of log ID {existing_correct_log.id}',
                    'camper': log.bunk_assignment.camper if hasattr(log.bunk_assignment, 'camper') else 'Unknown',
                    'created_at': timezone.localtime(log.created_at),
                })
            else:
                # No duplicate - mark for date update
                logs_to_update.append({
                    'log': log,
                    'camper': log.bunk_assignment.camper if hasattr(log.bunk_assignment, 'camper') else 'Unknown',
                    'created_at': timezone.localtime(log.created_at),
                })

        # Report findings
        self.stdout.write(f"\nAnalysis Results:")
        self.stdout.write(f"- Logs to DELETE (duplicates): {len(logs_to_delete)}")
        self.stdout.write(f"- Logs to UPDATE date: {len(logs_to_update)}")
        
        # Show details of logs to delete
        if logs_to_delete:
            self.stdout.write(f"\n{'[DRY RUN] ' if dry_run else ''}Logs to DELETE:")
            for item in logs_to_delete:
                self.stdout.write(
                    f"  - Log ID {item['log'].id}: {item['camper']} "
                    f"(created: {item['created_at']}) - {item['reason']}"
                )
        
        # Show details of logs to update
        if logs_to_update:
            self.stdout.write(f"\n{'[DRY RUN] ' if dry_run else ''}Logs to UPDATE date (2025-07-07 → 2025-07-06):")
            for item in logs_to_update:
                self.stdout.write(
                    f"  - Log ID {item['log'].id}: {item['camper']} "
                    f"(created: {item['created_at']})"
                )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"\n[DRY RUN] No changes made. Run with --force to apply changes."
                )
            )
            return

        # Confirm before making changes
        if not force:
            self.stdout.write(self.style.ERROR("Missing --force flag. No changes made."))
            return

        # Apply changes in a transaction
        try:
            with transaction.atomic():
                deleted_count = 0
                updated_count = 0
                
                # Delete duplicate logs
                for item in logs_to_delete:
                    log = item['log']
                    log_id = log.id
                    camper = item['camper']
                    log.delete()
                    deleted_count += 1
                    self.stdout.write(f"DELETED Log ID {log_id}: {camper}")
                
                # Update dates for non-duplicates
                for item in logs_to_update:
                    log = item['log']
                    old_date = log.date
                    log.date = correct_date
                    # Bypass our clean() validation for this admin fix
                    log.save(update_fields=['date'])
                    updated_count += 1
                    self.stdout.write(f"UPDATED Log ID {log.id}: {item['camper']} date {old_date} → {log.date}")
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nSuccessfully fixed production data:\n"
                        f"- Deleted {deleted_count} duplicate logs\n"
                        f"- Updated {updated_count} log dates\n"
                        f"- Total logs processed: {len(problematic_logs)}"
                    )
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error applying changes: {e}")
            )
            raise

        # Final verification
        remaining_problematic = BunkLog.objects.filter(date=problem_date)
        remaining_created_on_july_6 = []
        for log in remaining_problematic:
            local_created = timezone.localtime(log.created_at)
            if local_created.date() == correct_date:
                remaining_created_on_july_6.append(log)
        
        if remaining_created_on_july_6:
            self.stdout.write(
                self.style.WARNING(
                    f"WARNING: {len(remaining_created_on_july_6)} problematic logs still remain!"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("✅ All problematic logs have been fixed!")
            )
