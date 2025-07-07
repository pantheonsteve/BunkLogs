from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from bunk_logs.bunklogs.models import BunkLog


class Command(BaseCommand):
    help = 'Fix date conflicts by handling duplicates intelligently'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )
        parser.add_argument(
            '--strategy',
            choices=['merge', 'keep-latest', 'keep-oldest'],
            default='keep-latest',
            help='Strategy for handling conflicts (default: keep-latest)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        strategy = options['strategy']
        
        self.stdout.write(f'Running date conflict resolution with strategy: {strategy}')
        if dry_run:
            self.stdout.write('DRY RUN - No changes will be made\n')
        
        # Find all records that need date fixes
        all_records = BunkLog.objects.all().order_by('bunk_assignment_id', 'date')
        needs_fix = []
        
        for record in all_records:
            correct_date = timezone.localtime(record.created_at).date()
            if record.date != correct_date:
                needs_fix.append(record)
        
        self.stdout.write(f'Found {len(needs_fix)} records that need date fixes')
        
        # Group conflicts
        conflicts = {}
        for record in needs_fix:
            correct_date = timezone.localtime(record.created_at).date()
            
            # Check if there's already a record for this bunk_assignment on the correct date
            existing = BunkLog.objects.filter(
                bunk_assignment_id=record.bunk_assignment_id,
                date=correct_date
            ).exclude(id=record.id).first()
            
            if existing:
                key = (record.bunk_assignment_id, correct_date)
                if key not in conflicts:
                    conflicts[key] = []
                conflicts[key].append((record, existing))
        
        self.stdout.write(f'Found {len(conflicts)} conflict groups\n')
        
        fixed_count = 0
        deleted_count = 0
        
        with transaction.atomic():
            # Handle conflicts first
            for (bunk_assignment_id, target_date), conflict_pairs in conflicts.items():
                self.stdout.write(f'Resolving conflict for bunk {bunk_assignment_id} on {target_date}:')
                
                # Collect all records involved in this conflict
                all_conflict_records = []
                for record, existing in conflict_pairs:
                    all_conflict_records.extend([record, existing])
                
                # Remove duplicates and sort by creation time
                unique_records = list(set(all_conflict_records))
                unique_records.sort(key=lambda r: r.created_at)
                
                if strategy == 'keep-latest':
                    keeper = max(unique_records, key=lambda r: r.created_at)
                elif strategy == 'keep-oldest':
                    keeper = min(unique_records, key=lambda r: r.created_at)
                elif strategy == 'merge':
                    # Keep the one with the most data, or latest if tied
                    def score_record(r):
                        score = 0
                        if r.present is not None: score += 1
                        if r.behavior: score += 1
                        if r.notes: score += 1
                        return (score, r.created_at)
                    
                    keeper = max(unique_records, key=score_record)
                
                # Delete the others FIRST to avoid unique constraint violations
                to_delete = [r for r in unique_records if r.id != keeper.id]
                for record in to_delete:
                    self.stdout.write(f'  Deleting duplicate record {record.id} (created {record.created_at})')
                    if not dry_run:
                        record.delete()
                    deleted_count += 1
                
                # Then update keeper to correct date (now safe from constraints)
                if keeper.date != target_date:
                    self.stdout.write(f'  Updating record {keeper.id} date from {keeper.date} to {target_date}')
                    if not dry_run:
                        keeper.date = target_date
                        keeper.save()
                    fixed_count += 1
                
                self.stdout.write(f'  Kept record {keeper.id}, deleted {len(to_delete)} duplicates\n')
            
            # Handle records that don't have conflicts
            non_conflict_records = [r for r in needs_fix 
                                   if not any((r.bunk_assignment_id, timezone.localtime(r.created_at).date()) in conflicts
                                            for r in [r])]
            
            for record in non_conflict_records:
                correct_date = timezone.localtime(record.created_at).date()
                self.stdout.write(f'Fixing non-conflict record {record.id}: {record.date} -> {correct_date}')
                if not dry_run:
                    record.date = correct_date
                    record.save()
                fixed_count += 1
        
        if dry_run:
            self.stdout.write(f'\nDRY RUN SUMMARY:')
            self.stdout.write(f'Would fix {fixed_count} records')
            self.stdout.write(f'Would delete {deleted_count} duplicate records')
            self.stdout.write(f'\nRun without --dry-run to apply changes')
        else:
            self.stdout.write(f'\nSUCCESS:')
            self.stdout.write(f'Fixed {fixed_count} records')
            self.stdout.write(f'Deleted {deleted_count} duplicate records')
            self.stdout.write(f'Date synchronization complete!')
