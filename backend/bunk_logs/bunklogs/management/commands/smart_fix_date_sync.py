from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F
from bunklogs.models import BunkLog, CounselorLog
from collections import defaultdict


class Command(BaseCommand):
    help = 'Smart fix for date synchronization issues - handles duplicates intelligently'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without actually making changes',
        )

    def calculate_record_score(self, record):
        """Calculate a score for a record to determine which one to keep"""
        score = 0
        
        # Prefer records where date matches created_at (these are "correct")
        if record.date == record.created_at.date():
            score += 100
        
        # Prefer records with more content
        if hasattr(record, 'description') and record.description:
            score += len(record.description.strip()) * 0.1
        elif hasattr(record, 'elaboration') and record.elaboration:
            score += len(record.elaboration.strip()) * 0.1
            
        # Prefer more recent records (slight preference)
        score += record.created_at.timestamp() * 0.0001
        
        return score
    
    def get_description_field(self, record):
        """Get the appropriate description field for display"""
        if hasattr(record, 'description'):
            return record.description or ''
        elif hasattr(record, 'elaboration'):
            return record.elaboration or ''
        return ''

    def handle(self, *args, **options):
        self.stdout.write("Starting smart date synchronization fix...")
        
        # Stats
        bunk_fixed = 0
        bunk_deleted = 0
        counselor_fixed = 0
        counselor_deleted = 0
        
        with transaction.atomic():
            # Handle BunkLog duplicates
            self.stdout.write("\n=== Processing BunkLog records ===")
            
            # Group records by (bunk_assignment, date) to find conflicts
            bunk_groups = defaultdict(list)
            mismatched_bunks = BunkLog.objects.exclude(
                date=F('created_at__date')
            ).select_related('bunk_assignment')
            
            for log in mismatched_bunks:
                key = (log.bunk_assignment_id, log.date)
                bunk_groups[key].append(log)
            
            # Also check for records that would conflict after fixing dates
            all_bunks = BunkLog.objects.select_related('bunk_assignment')
            for log in all_bunks:
                correct_date = log.created_at.date()
                if log.date != correct_date:
                    # This record would be fixed to correct_date
                    # Check if there are other records with this date
                    key = (log.bunk_assignment_id, correct_date)
                    existing_with_correct_date = BunkLog.objects.filter(
                        bunk_assignment_id=log.bunk_assignment_id,
                        date=correct_date
                    ).exclude(id=log.id)
                    
                    if existing_with_correct_date.exists():
                        # There's a conflict - group them together
                        conflict_group = [log] + list(existing_with_correct_date)
                        bunk_groups[key] = conflict_group
            
            # Process conflicts
            for (bunk_assignment_id, date), records in bunk_groups.items():
                if len(records) <= 1:
                    continue
                    
                self.stdout.write(f"\nConflict for bunk_assignment {bunk_assignment_id}, date {date}:")
                
                # Calculate scores for all records
                scored_records = []
                for record in records:
                    score = self.calculate_record_score(record)
                    scored_records.append((record, score))
                
                # Sort by score (highest first)
                scored_records.sort(key=lambda x: x[1], reverse=True)
                
                # Keep the highest scoring record, delete others
                to_keep = scored_records[0][0]
                keep_score = scored_records[0][1]
                
                for record, delete_score in scored_records[1:]:
                    to_delete = record
                    
                    if options['dry_run']:
                        self.stdout.write(
                            f"    DELETE: {to_delete.id} (date={to_delete.date}, "
                            f"created={to_delete.created_at.date()}, score={delete_score})"
                        )
                        desc = self.get_description_field(to_delete)
                        self.stdout.write(f"            Description: '{desc[:100]}{'...' if len(desc) > 100 else ''}'")
                        self.stdout.write(
                            f"    KEEP:   {to_keep.id} (date={to_keep.date}, "
                            f"created={to_keep.created_at.date()}, score={keep_score})"
                        )
                        keep_desc = self.get_description_field(to_keep)
                        self.stdout.write(f"            Description: '{keep_desc[:100]}{'...' if len(keep_desc) > 100 else ''}'")
                        self.stdout.write("")  # Empty line for readability
                    else:
                        to_delete.delete()
                        bunk_deleted += 1
                        self.stdout.write(f"    Deleted duplicate record {to_delete.id}")
            
            # Fix remaining non-conflicting records
            remaining_mismatched = BunkLog.objects.exclude(
                date=F('created_at__date')
            )
            
            for log in remaining_mismatched:
                correct_date = log.created_at.date()
                
                # Check if this would create a conflict
                conflict_exists = BunkLog.objects.filter(
                    bunk_assignment=log.bunk_assignment,
                    date=correct_date
                ).exclude(id=log.id).exists()
                
                if not conflict_exists:
                    if options['dry_run']:
                        self.stdout.write(
                            f"Fix: BunkLog {log.id} date {log.date} → {correct_date}"
                        )
                        desc = self.get_description_field(log)
                        self.stdout.write(f"     Description: '{desc[:100]}{'...' if len(desc) > 100 else ''}'")
                    else:
                        log.date = correct_date
                        log.save()
                        bunk_fixed += 1
            
            # Handle CounselorLog records similarly
            self.stdout.write("\n=== Processing CounselorLog records ===")
            
            # Group records by (unit_staff_assignment, date) to find conflicts
            counselor_groups = defaultdict(list)
            mismatched_counselors = CounselorLog.objects.exclude(
                date=F('created_at__date')
            ).select_related('unit_staff_assignment')
            
            for log in mismatched_counselors:
                key = (log.unit_staff_assignment_id, log.date)
                counselor_groups[key].append(log)
            
            # Check for potential conflicts after fixing
            all_counselors = CounselorLog.objects.select_related('unit_staff_assignment')
            for log in all_counselors:
                correct_date = log.created_at.date()
                if log.date != correct_date:
                    key = (log.unit_staff_assignment_id, correct_date)
                    existing_with_correct_date = CounselorLog.objects.filter(
                        unit_staff_assignment_id=log.unit_staff_assignment_id,
                        date=correct_date
                    ).exclude(id=log.id)
                    
                    if existing_with_correct_date.exists():
                        conflict_group = [log] + list(existing_with_correct_date)
                        counselor_groups[key] = conflict_group
            
            # Process counselor conflicts
            for (unit_staff_assignment_id, date), records in counselor_groups.items():
                if len(records) <= 1:
                    continue
                    
                self.stdout.write(f"\nConflict for unit_staff_assignment {unit_staff_assignment_id}, date {date}:")
                
                scored_records = []
                for record in records:
                    score = self.calculate_record_score(record)
                    scored_records.append((record, score))
                
                scored_records.sort(key=lambda x: x[1], reverse=True)
                
                to_keep = scored_records[0][0]
                keep_score = scored_records[0][1]
                
                for record, delete_score in scored_records[1:]:
                    to_delete = record
                    
                    if options['dry_run']:
                        self.stdout.write(
                            f"    DELETE: {to_delete.id} (date={to_delete.date}, "
                            f"created={to_delete.created_at.date()}, score={delete_score})"
                        )
                        desc = self.get_description_field(to_delete)
                        self.stdout.write(f"            Description: '{desc[:100]}{'...' if len(desc) > 100 else ''}'")
                        self.stdout.write(
                            f"    KEEP:   {to_keep.id} (date={to_keep.date}, "
                            f"created={to_keep.created_at.date()}, score={keep_score})"
                        )
                        keep_desc = self.get_description_field(to_keep)
                        self.stdout.write(f"            Description: '{keep_desc[:100]}{'...' if len(keep_desc) > 100 else ''}'")
                        self.stdout.write("")
                    else:
                        to_delete.delete()
                        counselor_deleted += 1
                        self.stdout.write(f"    Deleted duplicate record {to_delete.id}")
            
            # Fix remaining non-conflicting counselor records
            remaining_counselor_mismatched = CounselorLog.objects.exclude(
                date=F('created_at__date')
            )
            
            for log in remaining_counselor_mismatched:
                correct_date = log.created_at.date()
                
                conflict_exists = CounselorLog.objects.filter(
                    unit_staff_assignment=log.unit_staff_assignment,
                    date=correct_date
                ).exclude(id=log.id).exists()
                
                if not conflict_exists:
                    if options['dry_run']:
                        self.stdout.write(
                            f"Fix: CounselorLog {log.id} date {log.date} → {correct_date}"
                        )
                        desc = self.get_description_field(log)
                        self.stdout.write(f"     Description: '{desc[:100]}{'...' if len(desc) > 100 else ''}'")
                    else:
                        log.date = correct_date
                        log.save()
                        counselor_fixed += 1
            
            if options['dry_run']:
                self.stdout.write("\n" + "="*50)
                self.stdout.write("DRY RUN COMPLETE - No changes made")
                self.stdout.write("="*50)
                self.stdout.write("To apply these changes, run without --dry-run")
            else:
                self.stdout.write("\n" + "="*50)
                self.stdout.write("SMART FIX COMPLETED")
                self.stdout.write("="*50)
                self.stdout.write(f"BunkLog records fixed: {bunk_fixed}")
                self.stdout.write(f"BunkLog duplicates deleted: {bunk_deleted}")
                self.stdout.write(f"CounselorLog records fixed: {counselor_fixed}")
                self.stdout.write(f"CounselorLog duplicates deleted: {counselor_deleted}")
