"""
Django management command to analyze BunkLog data for July 6-7, 2025 issues.

This command provides detailed analysis of BunkLogs around July 6-7, 2025
to understand the scope of the date-shifting problem.
"""

from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from django.utils import timezone
from datetime import date, datetime, timedelta
from bunk_logs.bunklogs.models import BunkLog


class Command(BaseCommand):
    help = 'Analyze BunkLog data for July 6-7, 2025 to understand date issues'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--start-date',
            type=str,
            default='2025-07-05',
            help='Start date for analysis (YYYY-MM-DD)',
        )
        parser.add_argument(
            '--end-date',
            type=str,
            default='2025-07-08',
            help='End date for analysis (YYYY-MM-DD)',
        )
    
    def handle(self, *args, **options):
        start_date = datetime.strptime(options['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(options['end_date'], '%Y-%m-%d').date()
        
        self.stdout.write(f"Analyzing BunkLogs from {start_date} to {end_date}")
        self.stdout.write("=" * 60)
        
        # Overall stats
        total_logs = BunkLog.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).count()
        
        self.stdout.write(f"Total BunkLogs in date range: {total_logs}")
        
        # Analyze by date
        current_date = start_date
        while current_date <= end_date:
            self.analyze_date(current_date)
            current_date += timedelta(days=1)
        
        # Look for potential duplicates
        self.stdout.write("\n" + "="*60)
        self.stdout.write("DUPLICATE ANALYSIS")
        self.stdout.write("="*60)
        
        # Find bunk_assignments with multiple logs on the same date
        duplicates = BunkLog.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).values('bunk_assignment', 'date').annotate(
            count=Count('id')
        ).filter(count__gt=1)
        
        if duplicates:
            self.stdout.write(f"Found {duplicates.count()} bunk_assignment/date combinations with multiple logs:")
            for dup in duplicates:
                logs = BunkLog.objects.filter(
                    bunk_assignment=dup['bunk_assignment'],
                    date=dup['date']
                ).select_related('bunk_assignment__camper')
                
                if logs.exists():
                    first_log = logs.first()
                    camper_name = f"{first_log.bunk_assignment.camper.first_name} {first_log.bunk_assignment.camper.last_name}"
                    self.stdout.write(f"  - {camper_name} on {dup['date']}: {dup['count']} logs")
                    
                    for log in logs:
                        self.stdout.write(f"    Log ID {log.id}, created: {log.created_at}")
        else:
            self.stdout.write("No duplicates found in the specified date range.")
        
        # Look for cross-date issues (July 6 creation, July 7 date)
        self.stdout.write("\n" + "="*60)
        self.stdout.write("CROSS-DATE ANALYSIS")
        self.stdout.write("="*60)
        
        july_6_created = date(2025, 7, 6)
        july_7_dated = date(2025, 7, 7)
        
        cross_date_logs = BunkLog.objects.filter(
            created_at__date=july_6_created,
            date=july_7_dated
        ).select_related('bunk_assignment__camper')
        
        self.stdout.write(f"BunkLogs created on July 6 but dated July 7: {cross_date_logs.count()}")
        
        if cross_date_logs.exists():
            self.stdout.write("Sample of problematic logs:")
            for log in cross_date_logs[:10]:  # Show first 10
                camper_name = f"{log.bunk_assignment.camper.first_name} {log.bunk_assignment.camper.last_name}"
                self.stdout.write(f"  - Log ID {log.id}: {camper_name}, created: {log.created_at}, dated: {log.date}")
        
        # Summary recommendations
        self.stdout.write("\n" + "="*60)
        self.stdout.write("RECOMMENDATIONS")
        self.stdout.write("="*60)
        
        if cross_date_logs.exists():
            self.stdout.write(f"⚠️  Found {cross_date_logs.count()} logs that need fixing")
            self.stdout.write("Recommended action: Run 'fix_july_7_bunklogs' command")
        else:
            self.stdout.write("✅ No cross-date issues found")
        
        if duplicates:
            self.stdout.write(f"⚠️  Found duplicate logs that may need manual review")
        else:
            self.stdout.write("✅ No duplicate logs found")
    
    def analyze_date(self, target_date):
        """Analyze BunkLogs for a specific date."""
        logs_on_date = BunkLog.objects.filter(date=target_date)
        logs_created_on_date = BunkLog.objects.filter(created_at__date=target_date)
        
        # Logs dated this date but created on different days
        created_elsewhere = logs_on_date.exclude(created_at__date=target_date)
        
        # Logs created this date but dated differently
        dated_elsewhere = logs_created_on_date.exclude(date=target_date)
        
        self.stdout.write(f"\n{target_date} Analysis:")
        self.stdout.write(f"  - Logs dated {target_date}: {logs_on_date.count()}")
        self.stdout.write(f"  - Logs created on {target_date}: {logs_created_on_date.count()}")
        
        if created_elsewhere.exists():
            self.stdout.write(f"  - Logs dated {target_date} but created elsewhere: {created_elsewhere.count()}")
            
        if dated_elsewhere.exists():
            self.stdout.write(f"  - Logs created on {target_date} but dated elsewhere: {dated_elsewhere.count()}")
            # Show where they're dated
            other_dates = dated_elsewhere.values('date').annotate(count=Count('id'))
            for item in other_dates:
                self.stdout.write(f"    → {item['count']} logs dated {item['date']}")
        
        # Creation time analysis for this date
        if logs_created_on_date.exists():
            earliest = logs_created_on_date.earliest('created_at')
            latest = logs_created_on_date.latest('created_at')
            self.stdout.write(f"  - Creation time span: {earliest.created_at.time()} to {latest.created_at.time()}")
