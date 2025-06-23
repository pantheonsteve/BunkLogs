"""
Management command for importing users from CSV files.
This can be used as an alternative to the admin interface for very large imports.
"""
from django.core.management.base import BaseCommand, CommandError
from pathlib import Path

from bunk_logs.users.services.imports import import_users_from_csv


class Command(BaseCommand):
    help = 'Import users from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help='Path to the CSV file containing user data'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Validate the import without saving to database',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=25,
            help='Number of users to process per batch (default: 25)',
        )
        parser.add_argument(
            '--no-fast-hashing',
            action='store_true',
            help='Disable fast password hashing (use secure but slower Argon2)',
        )

    def handle(self, *args, **options):
        csv_file = Path(options['csv_file'])
        
        if not csv_file.exists():
            raise CommandError(f'CSV file "{csv_file}" does not exist.')
        
        if not csv_file.suffix.lower() == '.csv':
            raise CommandError(f'File "{csv_file}" is not a CSV file.')

        self.stdout.write(f'Starting import from {csv_file}...')
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No data will be saved'))
        
        try:
            result = import_users_from_csv(
                csv_file,
                dry_run=options['dry_run'],
                batch_size=options['batch_size'],
                use_fast_hashing=not options['no_fast_hashing']
            )
            
            if options['dry_run']:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Dry run completed. {result["success_count"]} users would be imported.'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully imported {result["success_count"]} users.'
                    )
                )
            
            if result['error_count'] > 0:
                self.stdout.write(
                    self.style.WARNING(f'{result["error_count"]} errors occurred:')
                )
                for error in result['errors']:
                    self.stdout.write(
                        self.style.ERROR(f'  Row {error["row"]}: {error["error"]}')
                    )
        
        except Exception as e:
            raise CommandError(f'Import failed: {str(e)}')
