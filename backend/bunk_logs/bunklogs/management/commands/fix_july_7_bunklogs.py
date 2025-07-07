"""
Django management command to fix July 7th BunkLogs that were incorrectly created.

This command handles BunkLogs that were created on July 6, 2025 but incorrectly 
dated July 7, 2025 due to the old date-shifting logic.

Logic:
1. Find all BunkLogs dated July 7, 2025 that were created on July 6, 2025
2. For each July 7th log, check if there's already a July 6th log for the same camper
3. If duplicate exists: DELETE the July 7th log (it's incorrect)
4. If no duplicate: UPDATE the July 7th log's date to July 6th (fix the date)
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import date, datetime
from bunk_logs.bunklogs.models import BunkLog


class Command(BaseCommand):
    help = 'Fix BunkLogs dated July 7, 2025 that were incorrectly created on July 6, 2025'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Actually perform the fixes (required for real execution)',
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
        
        self.stdout.write(f"Running in {'DRY RUN' if dry_run else 'FORCE'} mode")
        self.stdout.write("-" * 50)
        
        # Define the problematic dates
        creation_date = date(2025, 7, 6)  # When they were created
        incorrect_date = date(2025, 7, 7)  # What they were incorrectly dated
        correct_date = date(2025, 7, 6)   # What they should be dated
        
        # Find all BunkLogs created on July 6 but dated July 7
        problematic_logs = BunkLog.objects.filter(
            date=incorrect_date,
            created_at__date=creation_date
        ).select_related('bunk_assignment__camper')
        
        self.stdout.write(f"Found {problematic_logs.count()} BunkLogs dated July 7th that were created on July 6th")
        
        if problematic_logs.count() == 0:
            self.stdout.write(self.style.SUCCESS("No problematic logs found. Nothing to fix."))
            return
        
        # Analyze each problematic log
        to_delete = []
        to_update = []
        
        for log in problematic_logs:
            camper_id = log.bunk_assignment.camper.id
            bunk_assignment_id = log.bunk_assignment.id
            
            # Check if there's already a July 6th log for this camper/bunk_assignment
            existing_july_6_log = BunkLog.objects.filter(
                bunk_assignment_id=bunk_assignment_id,
                date=correct_date
            ).first()
            
            if existing_july_6_log:
                # Duplicate exists - mark July 7th log for deletion
                to_delete.append({
                    'log': log,
                    'camper_name': f"{log.bunk_assignment.camper.first_name} {log.bunk_assignment.camper.last_name}",
                    'existing_log_id': existing_july_6_log.id
                })
            else:
                # No duplicate - mark July 7th log for date correction
                to_update.append({
                    'log': log,
                    'camper_name': f"{log.bunk_assignment.camper.first_name} {log.bunk_assignment.camper.last_name}",
                })
        
        # Report findings
        self.stdout.write(f"\nAnalysis Results:")
        self.stdout.write(f"- Logs to DELETE (duplicates): {len(to_delete)}")
        self.stdout.write(f"- Logs to UPDATE (fix date): {len(to_update)}")
        
        # Show details
        if to_delete:
            self.stdout.write(f"\nLogs to DELETE (because July 6th log exists):")
            for item in to_delete:
                self.stdout.write(
                    f"  - DELETE Log ID {item['log'].id} for {item['camper_name']} "
                    f"(July 6th log ID {item['existing_log_id']} already exists)"
                )
        
        if to_update:
            self.stdout.write(f"\nLogs to UPDATE (change date from July 7th to July 6th):")
            for item in to_update:
                self.stdout.write(
                    f"  - UPDATE Log ID {item['log'].id} for {item['camper_name']} "
                    f"(change date from {incorrect_date} to {correct_date})"
                )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"\nDRY RUN: No changes made. Use --force to execute these changes."
                )
            )
            return
        
        # Execute the fixes
        self.stdout.write(f"\nExecuting fixes...")
        
        with transaction.atomic():
            deleted_count = 0
            updated_count = 0
            
            # Delete duplicates
            for item in to_delete:
                log = item['log']
                log_id = log.id
                camper_name = item['camper_name']
                
                log.delete()
                deleted_count += 1
                self.stdout.write(f"✓ DELETED Log ID {log_id} for {camper_name}")
            
            # Update dates
            for item in to_update:
                log = item['log']
                log_id = log.id
                camper_name = item['camper_name']
                
                # Update the date directly in the database to avoid validation issues
                BunkLog.objects.filter(id=log.id).update(date=correct_date)
                updated_count += 1
                self.stdout.write(f"✓ UPDATED Log ID {log_id} for {camper_name} (date: {incorrect_date} → {correct_date})")
        
        # Final summary
        self.stdout.write(f"\n" + "="*50)
        self.stdout.write(self.style.SUCCESS(f"COMPLETED SUCCESSFULLY!"))
        self.stdout.write(f"- {deleted_count} logs deleted")
        self.stdout.write(f"- {updated_count} logs updated")
        self.stdout.write(f"- Total fixes applied: {deleted_count + updated_count}")
        
        # Verify the results
        remaining_july_7_logs = BunkLog.objects.filter(
            date=incorrect_date,
            created_at__date=creation_date
        ).count()
        
        if remaining_july_7_logs == 0:
            self.stdout.write(self.style.SUCCESS("✓ No problematic July 7th logs remain"))
        else:
            self.stdout.write(
                self.style.ERROR(f"⚠ WARNING: {remaining_july_7_logs} July 7th logs still exist")
            )
