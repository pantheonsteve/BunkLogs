"""
Django management command to backup BunkLogs before fixing production dates.

This creates a JSON backup of all BunkLogs from July 6-7, 2025 before making any changes.
"""

from django.core.management.base import BaseCommand
from django.core import serializers
from django.utils import timezone
from datetime import date
from bunk_logs.bunklogs.models import BunkLog
import json
import os


class Command(BaseCommand):
    help = 'Create backup of July 6-7 BunkLogs before fixing production dates'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='bunklogs_backup_july_6_7_2025.json',
            help='Output file for backup (default: bunklogs_backup_july_6_7_2025.json)',
        )

    def handle(self, *args, **options):
        output_file = options['output']
        
        # Get all BunkLogs from July 6-7, 2025
        july_6 = date(2025, 7, 6)
        july_7 = date(2025, 7, 7)
        
        logs_to_backup = BunkLog.objects.filter(
            date__in=[july_6, july_7]
        ).order_by('date', 'id')
        
        self.stdout.write(f"Found {logs_to_backup.count()} BunkLogs to backup from July 6-7, 2025")
        
        if logs_to_backup.count() == 0:
            self.stdout.write(self.style.WARNING("No logs found to backup"))
            return
        
        # Create backup data
        backup_data = {
            'backup_timestamp': timezone.now().isoformat(),
            'backup_description': 'BunkLogs from July 6-7, 2025 before date fix',
            'total_logs': logs_to_backup.count(),
            'logs': []
        }
        
        # Serialize the logs with additional metadata
        for log in logs_to_backup:
            log_data = {
                'id': log.id,
                'bunk_assignment_id': log.bunk_assignment_id,
                'date': log.date.isoformat(),
                'counselor_id': log.counselor_id,
                'not_on_camp': log.not_on_camp,
                'social_score': log.social_score,
                'behavior_score': log.behavior_score,
                'participation_score': log.participation_score,
                'request_camper_care_help': log.request_camper_care_help,
                'request_unit_head_help': log.request_unit_head_help,
                'description': log.description,
                'created_at': log.created_at.isoformat(),
                'updated_at': log.updated_at.isoformat(),
                # Additional metadata for debugging
                'created_at_date': timezone.localtime(log.created_at).date().isoformat(),
                'is_problematic': (
                    log.date == july_7 and 
                    timezone.localtime(log.created_at).date() == july_6
                )
            }
            backup_data['logs'].append(log_data)
        
        # Write backup file
        try:
            with open(output_file, 'w') as f:
                json.dump(backup_data, f, indent=2, default=str)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Backup created successfully: {output_file}\n"
                    f"   - Total logs backed up: {backup_data['total_logs']}\n"
                    f"   - Problematic logs: {sum(1 for log in backup_data['logs'] if log['is_problematic'])}\n"
                    f"   - File size: {os.path.getsize(output_file)} bytes"
                )
            )
            
            # Show some statistics
            july_6_count = sum(1 for log in backup_data['logs'] if log['date'] == july_6.isoformat())
            july_7_count = sum(1 for log in backup_data['logs'] if log['date'] == july_7.isoformat())
            
            self.stdout.write(f"\nBackup Statistics:")
            self.stdout.write(f"  - July 6 dated logs: {july_6_count}")
            self.stdout.write(f"  - July 7 dated logs: {july_7_count}")
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Failed to create backup: {e}")
            )
            raise
