from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from bunk_logs.bunklogs.models import BunkLog, CounselorLog


class Command(BaseCommand):
    help = 'Fix date fields to match the date from created_at (with recursive duplicate resolution)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=None,
            help='Process records in batches of this size (useful for large datasets)',
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.batch_size = options.get('batch_size')
        self.fixed_ids = set()  # Track which records we've already fixed
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        if self.batch_size:
            self.stdout.write(f'Processing in batches of {self.batch_size}')
        
        # Find BunkLogs where the date doesn't match created_at date
        bunk_logs_to_fix = []
        for log in BunkLog.objects.all():
            correct_date = timezone.localtime(log.created_at).date()
            if log.date != correct_date:
                bunk_logs_to_fix.append(log)
        
        self.stdout.write(f'Found {len(bunk_logs_to_fix)} BunkLog records to fix')
        
        fixed_count = 0
        skipped_count = 0
        
        # Process in batches if specified
        if self.batch_size:
            for i in range(0, len(bunk_logs_to_fix), self.batch_size):
                batch = bunk_logs_to_fix[i:i + self.batch_size]
                self.stdout.write(f'Processing batch {i//self.batch_size + 1}: records {i+1}-{min(i+self.batch_size, len(bunk_logs_to_fix))}')
                
                for log in batch:
                    if log.id in self.fixed_ids:
                        continue  # Already fixed this one
                        
                    result = self.fix_bunklog_recursive(log)
                    if result == 'fixed':
                        fixed_count += 1
                    elif result == 'skipped':
                        skipped_count += 1
        else:
            for log in bunk_logs_to_fix:
                if log.id in self.fixed_ids:
                    continue  # Already fixed this one
                    
                result = self.fix_bunklog_recursive(log)
                if result == 'fixed':
                    fixed_count += 1
                elif result == 'skipped':
                    skipped_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Fixed {fixed_count} BunkLog records'))
        if skipped_count > 0:
            self.stdout.write(self.style.WARNING(f'Skipped {skipped_count} BunkLog records due to conflicts'))

        fixed_count = 0
        skipped_count = 0

        # Process CounselorLogs in batches
        counselor_logs_to_fix = CounselorLog.objects.all()
        total_counselor_logs = counselor_logs_to_fix.count()
        self.stdout.write(f'Found {total_counselor_logs} CounselorLog records to fix')
        
        if self.batch_size:
            for i in range(0, total_counselor_logs, self.batch_size):
                batch = counselor_logs_to_fix[i:i + self.batch_size]
                self.stdout.write(f'Processing batch {i//self.batch_size + 1}: records {i+1}-{min(i+self.batch_size, total_counselor_logs)}')
                
                for log in batch:
                    correct_date = timezone.localtime(log.created_at).date()
                    if log.date != correct_date:
                        result = self.fix_counselorlog_recursive(log)
                        if result == 'fixed':
                            fixed_count += 1
                        elif result == 'skipped':
                            skipped_count += 1
        else:
            for log in counselor_logs_to_fix:
                correct_date = timezone.localtime(log.created_at).date()
                if log.date != correct_date:
                    result = self.fix_counselorlog_recursive(log)
                    if result == 'fixed':
                        fixed_count += 1
                    elif result == 'skipped':
                        skipped_count += 1

        self.stdout.write(self.style.SUCCESS(f'Fixed {fixed_count} CounselorLog records'))
        if skipped_count > 0:
            self.stdout.write(self.style.WARNING(f'Skipped {skipped_count} CounselorLog records due to conflicts'))

    def fix_bunklog_recursive(self, log, depth=0):
        """Recursively fix a BunkLog, handling duplicates by fixing them first"""
        if depth > 10:  # Prevent infinite recursion
            self.stdout.write(
                self.style.ERROR(f'Max recursion depth reached for BunkLog {log.id}')
            )
            return 'skipped'
        
        if log.id in self.fixed_ids:
            return 'already_fixed'
        
        correct_date = timezone.localtime(log.created_at).date()
        
        if log.date == correct_date:
            return 'already_correct'
        
        if self.dry_run:
            self.stdout.write(f'{"  " * depth}Would fix BunkLog {log.id}: {log.date} → {correct_date}')
            return 'fixed'
        
        # Check if there's a conflicting record
        conflicting_log = BunkLog.objects.filter(
            bunk_assignment_id=log.bunk_assignment_id,
            date=correct_date
        ).exclude(id=log.id).first()
        
        if conflicting_log:
            self.stdout.write(
                f'{"  " * depth}BunkLog {log.id} conflicts with {conflicting_log.id}, fixing conflict first...'
            )
            
            # Recursively fix the conflicting record first
            conflict_result = self.fix_bunklog_recursive(conflicting_log, depth + 1)
            
            if conflict_result not in ['fixed', 'already_fixed', 'already_correct']:
                self.stdout.write(
                    self.style.ERROR(f'{"  " * depth}Could not resolve conflict for BunkLog {log.id}')
                )
                return 'skipped'
        
        # Now try to fix our record
        try:
            old_date = log.date
            log.date = correct_date
            log.save()
            self.fixed_ids.add(log.id)
            self.stdout.write(
                f'{"  " * depth}Fixed BunkLog {log.id}: {old_date} → {correct_date}'
            )
            return 'fixed'
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'{"  " * depth}Error fixing BunkLog {log.id}: {e}')
            )
            return 'skipped'

    def fix_counselorlog_recursive(self, log, depth=0):
        """Recursively fix a CounselorLog, handling duplicates by fixing them first"""
        if depth > 10:  # Prevent infinite recursion
            self.stdout.write(
                self.style.ERROR(f'Max recursion depth reached for CounselorLog {log.id}')
            )
            return 'skipped'
        
        correct_date = timezone.localtime(log.created_at).date()
        
        if log.date == correct_date:
            return 'already_correct'
        
        if self.dry_run:
            self.stdout.write(f'{"  " * depth}Would fix CounselorLog {log.id}: {log.date} → {correct_date}')
            return 'fixed'
        
        # Check if there's a conflicting record
        conflicting_log = CounselorLog.objects.filter(
            counselor_id=log.counselor_id,
            date=correct_date
        ).exclude(id=log.id).first()
        
        if conflicting_log:
            self.stdout.write(
                f'{"  " * depth}CounselorLog {log.id} conflicts with {conflicting_log.id}, fixing conflict first...'
            )
            
            # Recursively fix the conflicting record first
            conflict_result = self.fix_counselorlog_recursive(conflicting_log, depth + 1)
            
            if conflict_result not in ['fixed', 'already_fixed', 'already_correct']:
                self.stdout.write(
                    self.style.ERROR(f'{"  " * depth}Could not resolve conflict for CounselorLog {log.id}')
                )
                return 'skipped'
        
        # Now try to fix our record
        try:
            old_date = log.date
            log.date = correct_date
            log.save()
            self.stdout.write(
                f'{"  " * depth}Fixed CounselorLog {log.id}: {old_date} → {correct_date}'
            )
            return 'fixed'
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'{"  " * depth}Error fixing CounselorLog {log.id}: {e}')
            )
            return 'skipped'
