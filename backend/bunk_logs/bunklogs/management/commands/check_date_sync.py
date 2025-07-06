from django.core.management.base import BaseCommand
from django.utils import timezone
from bunk_logs.bunklogs.models import BunkLog


class Command(BaseCommand):
    help = 'Check for BunkLog records with mismatched date and created_at fields'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("🔍 Checking for BunkLog records with mismatched date and created_at fields..."))
        self.stdout.write("=" * 80)
        
        # Get all BunkLog records
        all_logs = BunkLog.objects.all().order_by('-created_at')
        total_logs = all_logs.count()
        self.stdout.write(f"Total BunkLog records: {total_logs}")
        
        # Find mismatched records
        mismatched_logs = []
        
        for log in all_logs:
            # Convert created_at to date (in local timezone)
            created_date = timezone.localtime(log.created_at).date()
            log_date = log.date
            
            if created_date != log_date:
                camper_name = f"{log.bunk_assignment.camper.first_name} {log.bunk_assignment.camper.last_name}"
                counselor_name = log.counselor.get_full_name() if hasattr(log.counselor, 'get_full_name') else str(log.counselor)
                
                # Get bunk name safely
                bunk_name = "Unknown"
                try:
                    if hasattr(log.bunk_assignment, 'bunk') and log.bunk_assignment.bunk:
                        bunk_name = log.bunk_assignment.bunk.name
                except:
                    pass
                
                mismatched_logs.append({
                    'id': log.id,
                    'camper': camper_name,
                    'counselor': counselor_name,
                    'log_date': log_date,
                    'created_date': created_date,
                    'created_at': log.created_at,
                    'created_at_local': timezone.localtime(log.created_at),
                    'bunk': bunk_name,
                    'description': log.description[:100] + '...' if len(log.description) > 100 else log.description
                })
        
        self.stdout.write(f"Found {len(mismatched_logs)} records with mismatched dates\n")
        
        if mismatched_logs:
            self.stdout.write("📋 Mismatched Records (most recent first):")
            self.stdout.write("=" * 120)
            self.stdout.write(f"{'ID':<6} {'Camper':<20} {'Counselor':<20} {'Log Date':<12} {'Created Date':<12} {'Created At':<20}")
            self.stdout.write("-" * 120)
            
            for log in mismatched_logs:
                created_local_str = log['created_at_local'].strftime('%Y-%m-%d %H:%M')
                camper_truncated = log['camper'][:19] if len(log['camper']) > 19 else log['camper']
                counselor_truncated = log['counselor'][:19] if len(log['counselor']) > 19 else log['counselor']
                
                self.stdout.write(
                    f"{log['id']:<6} {camper_truncated:<20} {counselor_truncated:<20} "
                    f"{log['log_date']:<12} {log['created_date']:<12} {created_local_str:<20}"
                )
            
            self.stdout.write("\n📊 Summary by difference:")
            self.stdout.write("-" * 50)
            
            # Group by date difference
            differences = {}
            for log in mismatched_logs:
                diff = (log['log_date'] - log['created_date']).days
                if diff not in differences:
                    differences[diff] = []
                differences[diff].append(log)
            
            for diff, logs in sorted(differences.items()):
                if diff > 0:
                    self.stdout.write(f"Log date {diff} day(s) AFTER created date: {len(logs)} records")
                elif diff < 0:
                    self.stdout.write(f"Log date {abs(diff)} day(s) BEFORE created date: {len(logs)} records")
            
            self.stdout.write(f"\n📊 Recent examples (first 5 mismatched):")
            self.stdout.write("-" * 80)
            for log in mismatched_logs[:5]:
                diff = (log['log_date'] - log['created_date']).days
                direction = "after" if diff > 0 else "before"
                self.stdout.write(f"ID {log['id']}: {log['camper']} - Log date {abs(diff)} day(s) {direction} creation")
                self.stdout.write(f"   Log date: {log['log_date']}, Created: {log['created_date']} at {log['created_at_local'].strftime('%H:%M')}")
                self.stdout.write(f"   Description: {log['description'] or 'No description'}")
                self.stdout.write("")
        else:
            self.stdout.write(self.style.SUCCESS("✅ All BunkLog records have matching date and created_at fields!"))
        
        # Also check timezone handling
        self.stdout.write("\n🌍 Timezone Information:")
        self.stdout.write(f"Current timezone: {timezone.get_current_timezone()}")
        
        self.stdout.write(self.style.SUCCESS(f"\n✅ Analysis complete. Found {len(mismatched_logs)} mismatched records."))
        
        if mismatched_logs:
            self.stdout.write("\n💡 To fix these mismatches, run:")
            self.stdout.write("   python manage.py fix_date_sync --dry-run  (to preview changes)")
            self.stdout.write("   python manage.py fix_date_sync            (to apply changes)")
