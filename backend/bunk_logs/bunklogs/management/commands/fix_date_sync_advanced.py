from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from bunk_logs.bunklogs.models import BunkLog


class Command(BaseCommand):
    help = 'Fix BunkLog records with mismatched date and created_at fields (handles duplicates)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )
        parser.add_argument(
            '--delete-duplicates',
            action='store_true',
            help='Delete duplicate records when fixing dates',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        delete_duplicates = options['delete_duplicates']
        
        self.stdout.write("🔧 Fixing BunkLog date mismatches...")
        self.stdout.write("This will update the 'date' field to match the 'created_at' date")
        self.stdout.write("The created_at field will be used as the source of truth.")
        self.stdout.write("")
        
        # Find records that need updating
        mismatched_logs = []
        for log in BunkLog.objects.all().order_by('created_at'):
            created_date = timezone.localtime(log.created_at).date()
            if log.date != created_date:
                mismatched_logs.append({
                    'log': log,
                    'old_date': log.date,
                    'new_date': created_date
                })
        
        if not mismatched_logs:
            self.stdout.write(self.style.SUCCESS("✅ All records are already in sync!"))
            return
        
        self.stdout.write(f"Found {len(mismatched_logs)} records that need updating")
        
        # Group by potential conflicts (same bunk_assignment + new_date)
        potential_conflicts = {}
        for item in mismatched_logs:
            log = item['log']
            key = (log.bunk_assignment_id, item['new_date'])
            if key not in potential_conflicts:
                potential_conflicts[key] = []
            potential_conflicts[key].append(item)
        
        # Find actual conflicts (where fixing would create duplicates)
        conflicts = []
        safe_updates = []
        
        for key, items in potential_conflicts.items():
            bunk_assignment_id, target_date = key
            
            # Check if there's already a record with this bunk_assignment + target_date
            existing = BunkLog.objects.filter(
                bunk_assignment_id=bunk_assignment_id,
                date=target_date
            ).exclude(id__in=[item['log'].id for item in items]).first()
            
            if existing or len(items) > 1:
                # This would create a conflict
                conflicts.extend(items)
            else:
                # Safe to update
                safe_updates.extend(items)
        
        self.stdout.write(f"\n📊 Analysis:")
        self.stdout.write(f"Safe to update: {len(safe_updates)} records")
        self.stdout.write(f"Would create conflicts: {len(conflicts)} records")
        
        if conflicts:
            self.stdout.write(f"\n⚠️  Conflicting records:")
            self.stdout.write("-" * 80)
            for item in conflicts:
                log = item['log']
                camper_name = f"{log.bunk_assignment.camper.first_name} {log.bunk_assignment.camper.last_name}"
                self.stdout.write(f"ID {log.id}: {camper_name}")
                self.stdout.write(f"   Current date: {item['old_date']} -> Would change to: {item['new_date']}")
                self.stdout.write(f"   Created at: {timezone.localtime(log.created_at)}")
                self.stdout.write("")
                
            if delete_duplicates:
                self.stdout.write("Will handle conflicts by keeping the earliest created record and deleting duplicates.")
            else:
                self.stdout.write("Use --delete-duplicates flag to handle conflicts by deleting duplicate records.")
        
        if safe_updates:
            self.stdout.write(f"\n✅ Safe updates:")
            self.stdout.write("-" * 80)
            for item in safe_updates[:10]:  # Show first 10
                log = item['log']
                camper_name = f"{log.bunk_assignment.camper.first_name} {log.bunk_assignment.camper.last_name}"
                self.stdout.write(f"ID {log.id}: {camper_name}")
                self.stdout.write(f"   Current date: {item['old_date']} -> Will change to: {item['new_date']}")
                self.stdout.write("")
            
            if len(safe_updates) > 10:
                self.stdout.write(f"... and {len(safe_updates) - 10} more")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("\nDRY RUN: No changes were made."))
            self.stdout.write("Use without --dry-run to apply safe fixes.")
            if conflicts and not delete_duplicates:
                self.stdout.write("Add --delete-duplicates to also handle conflicts.")
            return
        
        # Apply safe updates
        updated_count = 0
        if safe_updates:
            self.stdout.write(f"\nApplying {len(safe_updates)} safe updates...")
            for item in safe_updates:
                log = item['log']
                BunkLog.objects.filter(pk=log.pk).update(date=item['new_date'])
                self.stdout.write(f"Updated ID {log.id}: {item['old_date']} -> {item['new_date']}")
                updated_count += 1
        
        # Handle conflicts if requested
        deleted_count = 0
        if conflicts and delete_duplicates:
            self.stdout.write(f"\nHandling {len(conflicts)} conflicts...")
            
            # Group conflicts by (bunk_assignment, target_date)
            conflict_groups = {}
            for item in conflicts:
                log = item['log']
                key = (log.bunk_assignment_id, item['new_date'])
                if key not in conflict_groups:
                    conflict_groups[key] = []
                conflict_groups[key].append(item)
            
            with transaction.atomic():
                for key, items in conflict_groups.items():
                    bunk_assignment_id, target_date = key
                    
                    # Find existing record with correct date
                    existing = BunkLog.objects.filter(
                        bunk_assignment_id=bunk_assignment_id,
                        date=target_date
                    ).exclude(id__in=[item['log'].id for item in items]).first()
                    
                    # Add existing to items for comparison
                    all_records = items.copy()
                    if existing:
                        all_records.append({
                            'log': existing,
                            'old_date': existing.date,
                            'new_date': target_date
                        })
                    
                    # Sort by created_at to keep the earliest
                    all_records.sort(key=lambda x: x['log'].created_at)
                    
                    # Keep the first (earliest created), delete the rest
                    to_keep = all_records[0]
                    to_delete = all_records[1:]
                    
                    self.stdout.write(f"For {to_keep['log'].bunk_assignment.camper.first_name} {to_keep['log'].bunk_assignment.camper.last_name} on {target_date}:")
                    self.stdout.write(f"  Keeping ID {to_keep['log'].id} (created {timezone.localtime(to_keep['log'].created_at)})")
                    
                    for item in to_delete:
                        log = item['log']
                        self.stdout.write(f"  Deleting ID {log.id} (created {timezone.localtime(log.created_at)})")
                        log.delete()
                        deleted_count += 1
                    
                    # Update the kept record's date if needed
                    if to_keep['log'].date != target_date:
                        BunkLog.objects.filter(pk=to_keep['log'].pk).update(date=target_date)
                        self.stdout.write(f"  Updated date for ID {to_keep['log'].id}: {to_keep['old_date']} -> {target_date}")
                        updated_count += 1
        
        self.stdout.write(self.style.SUCCESS(f"\n✅ Complete!"))
        self.stdout.write(f"Updated {updated_count} records")
        if deleted_count:
            self.stdout.write(f"Deleted {deleted_count} duplicate records")
        
        return f"Updated {updated_count} records, deleted {deleted_count} duplicates"
