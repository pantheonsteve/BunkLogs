from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from bunk_logs.bunklogs.models import BunkLog, CounselorLog
from collections import defaultdict


class Command(BaseCommand):
    help = 'Fix BunkLog and CounselorLog records with smart conflict resolution'

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

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        batch_size = options['batch_size']
        
        mode = "DRY RUN" if dry_run else "LIVE"
        self.stdout.write(self.style.WARNING(f"🔧 Smart date sync fix - {mode} MODE"))
        self.stdout.write("=" * 80)
        
        self.fix_bunklogs_smart(dry_run, batch_size)

    def fix_bunklogs_smart(self, dry_run, batch_size):
        self.stdout.write(self.style.SUCCESS("📋 Processing BunkLog records with smart conflict resolution..."))
        
        # Step 1: Find all mismatched records and group by potential conflicts
        conflicts = defaultdict(list)
        simple_fixes = []
        
        for log in BunkLog.objects.all().order_by('id'):
            created_date = timezone.localtime(log.created_at).date()
            if log.date != created_date:
                # Check if fixing this would create a conflict
                existing = BunkLog.objects.filter(
                    bunk_assignment_id=log.bunk_assignment_id, 
                    date=created_date
                ).exclude(id=log.id).first()
                
                if existing:
                    # There's a conflict - group them together
                    key = (log.bunk_assignment_id, created_date)
                    conflicts[key].append({
                        'id': log.id,
                        'current_date': log.date,
                        'target_date': created_date,
                        'created_at': log.created_at,
                        'log': log,
                        'type': 'mismatched'
                    })
                    # Also add the existing record to the conflict group if not already there
                    existing_added = False
                    for existing_record in conflicts[key]:
                        if existing_record['id'] == existing.id:
                            existing_added = True
                            break
                    
                    if not existing_added:
                        conflicts[key].append({
                            'id': existing.id,
                            'current_date': existing.date,
                            'target_date': timezone.localtime(existing.created_at).date(),
                            'created_at': existing.created_at,
                            'log': existing,
                            'type': 'existing'
                        })
                else:
                    # No conflict - can fix directly
                    simple_fixes.append({
                        'id': log.id,
                        'old_date': log.date,
                        'new_date': created_date,
                        'log': log
                    })

        self.stdout.write(f"Found {len(simple_fixes)} records for simple fixes")
        self.stdout.write(f"Found {len(conflicts)} conflict groups requiring resolution")
        
        # Step 2: Handle simple fixes first
        if simple_fixes:
            self.stdout.write("\n🔧 Applying simple fixes...")
            
            if not dry_run:
                fixed_count = 0
                for i in range(0, len(simple_fixes), batch_size):
                    batch = simple_fixes[i:i + batch_size]
                    
                    with transaction.atomic():
                        for item in batch:
                            try:
                                BunkLog.objects.filter(pk=item['id']).update(date=item['new_date'])
                                fixed_count += 1
                            except Exception as e:
                                self.stdout.write(
                                    self.style.ERROR(f"Error fixing BunkLog ID {item['id']}: {e}")
                                )
                    
                    self.stdout.write(f"Fixed simple batch {i//batch_size + 1}: {len(batch)} records")
                
                self.stdout.write(self.style.SUCCESS(f"✅ Fixed {fixed_count} simple records"))
            else:
                # Show examples for dry run
                for i, item in enumerate(simple_fixes[:5]):
                    try:
                        camper_name = f"{item['log'].bunk_assignment.camper.first_name} {item['log'].bunk_assignment.camper.last_name}"
                    except:
                        camper_name = "Unknown"
                    self.stdout.write(f"  ID {item['id']}: {camper_name} - {item['old_date']} → {item['new_date']}")
                
                if len(simple_fixes) > 5:
                    self.stdout.write(f"  ... and {len(simple_fixes) - 5} more")

        # Step 3: Handle conflicts with resolution strategy
        if conflicts:
            self.stdout.write("\n🛠️ Resolving conflicts...")
            
            resolved_count = 0
            deleted_count = 0
            
            for key, conflict_records in conflicts.items():
                bunk_assignment_id, target_date = key
                
                # Remove duplicates from conflict group (by ID)
                unique_records = {}
                for record in conflict_records:
                    if record['id'] not in unique_records:
                        unique_records[record['id']] = record
                
                conflict_records = list(unique_records.values())
                
                if len(conflict_records) < 2:
                    continue
                
                # Sort by quality score and creation time
                conflict_records.sort(key=lambda x: (
                    self.calculate_record_score(x['log']),
                    x['created_at']
                ), reverse=True)
                
                # Keep the best record, delete/update others
                keeper = conflict_records[0]
                to_remove = conflict_records[1:]
                
                try:
                    bunk_assignment = BunkLog.objects.get(id=keeper['id']).bunk_assignment
                    camper_name = f"{bunk_assignment.camper.first_name} {bunk_assignment.camper.last_name}"
                except:
                    camper_name = "Unknown"
                
                if dry_run:
                    self.stdout.write(f"  Conflict for {camper_name} on {target_date}:")
                    self.stdout.write(f"    KEEP: ID {keeper['id']} (score: {self.calculate_record_score(keeper['log']):.1f}, created {keeper['created_at'].strftime('%Y-%m-%d %H:%M')})")
                    for record in to_remove:
                        self.stdout.write(f"    DELETE: ID {record['id']} (score: {self.calculate_record_score(record['log']):.1f}, created {record['created_at'].strftime('%Y-%m-%d %H:%M')})")
                else:
                    try:
                        with transaction.atomic():
                            # Update the keeper's date if needed
                            if keeper['current_date'] != target_date:
                                BunkLog.objects.filter(pk=keeper['id']).update(date=target_date)
                                resolved_count += 1
                            
                            # Delete the conflicting records
                            for record in to_remove:
                                BunkLog.objects.filter(pk=record['id']).delete()
                                deleted_count += 1
                                
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"Error resolving conflict for {camper_name}: {e}")
                        )
            
            if not dry_run:
                self.stdout.write(self.style.SUCCESS(f"✅ Resolved {len(conflicts)} conflicts"))
                self.stdout.write(self.style.SUCCESS(f"✅ Updated {resolved_count} records"))
                self.stdout.write(self.style.SUCCESS(f"✅ Deleted {deleted_count} duplicate records"))
        
        if dry_run:
            self.stdout.write("\n💡 Run without --dry-run to apply these changes")
        else:
            self.stdout.write("\n✅ Smart date sync fix completed!")

    def calculate_record_score(self, log):
        """Calculate a score for a record to determine which one to keep in conflicts"""
        score = 0
        
        # Prefer records with more content
        if log.description and log.description.strip():
            score += 10
        
        # Add bonus for records with scores filled in
        if log.social_score:
            score += 3
        if log.behavior_score:
            score += 3
        if log.participation_score:
            score += 3
        
        # Prefer records where date matches created_at (these are "correct")
        created_date = timezone.localtime(log.created_at).date()
        if log.date == created_date:
            score += 20
        
        # Add small bonus for newer records (if all else is equal)
        score += log.id * 0.001
        
        return score
