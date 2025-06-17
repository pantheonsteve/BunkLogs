"""
Django management command to import test data from CSVs.

This command demonstrates how to use the test data functionality
when importing data from CSV files.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
import os

from bunk_logs.utils.csv_import import import_csv_with_test_flag
from bunk_logs.campers.models import Camper
from bunk_logs.users.models import User
from bunk_logs.bunks.models import Cabin, Session, Unit


class Command(BaseCommand):
    help = 'Import test data from CSV files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-file',
            type=str,
            required=True,
            help='Path to the CSV file to import',
        )
        parser.add_argument(
            '--model',
            type=str,
            required=True,
            choices=['users', 'campers', 'cabins', 'sessions', 'units'],
            help='Model to import data into',
        )
        parser.add_argument(
            '--test-data',
            action='store_true',
            help='Mark imported data as test data (recommended for testing)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without actually importing',
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        model_type = options['model']
        is_test_data = options['test_data']
        dry_run = options['dry_run']

        if not os.path.exists(csv_file):
            raise CommandError(f'CSV file not found: {csv_file}')

        # Define field mappings for each model
        field_mappings = {
            'users': {
                'email': 'email',
                'first_name': 'first_name',
                'last_name': 'last_name',
                'role': 'role',
            },
            'campers': {
                'first_name': 'first_name',
                'last_name': 'last_name',
                'date_of_birth': 'date_of_birth',
                'emergency_contact_name': 'emergency_contact_name',
                'emergency_contact_phone': 'emergency_contact_phone',
            },
            'cabins': {
                'name': 'name',
                'capacity': 'capacity',
                'location': 'location',
                'notes': 'notes',
            },
            'sessions': {
                'name': 'name',
                'start_date': 'start_date',
                'end_date': 'end_date',
                'is_active': 'is_active',
            },
            'units': {
                'name': 'name',
            },
        }

        # Define models
        models = {
            'users': User,
            'campers': Camper,
            'cabins': Cabin,
            'sessions': Session,
            'units': Unit,
        }

        # Define unique fields for duplicate detection
        unique_fields = {
            'users': ['email'],
            'campers': ['first_name', 'last_name'],
            'cabins': ['name'],
            'sessions': ['name'],
            'units': ['name'],
        }

        model_class = models[model_type]
        field_mapping = field_mappings[model_type]
        unique_field_list = unique_fields[model_type]

        self.stdout.write(f"Importing {model_type} from {csv_file}")
        self.stdout.write(f"Test data flag: {is_test_data}")
        self.stdout.write(f"Dry run: {dry_run}")

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "DRY RUN MODE - No data will be imported"
                )
            )
            # TODO: Add preview functionality
            return

        try:
            with transaction.atomic():
                result = import_csv_with_test_flag(
                    csv_file,
                    model_class,
                    field_mapping,
                    is_test_data=is_test_data,
                    unique_fields=unique_field_list,
                    update_existing=False
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Import completed successfully!"
                    )
                )
                self.stdout.write(f"  Created: {result['created']} records")
                self.stdout.write(f"  Updated: {result['updated']} records") 
                self.stdout.write(f"  Skipped: {result['skipped']} records")
                self.stdout.write(f"  Total processed: {result['total_processed']} records")

                if result['errors']:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Errors encountered: {len(result['errors'])}"
                        )
                    )
                    for error in result['errors']:
                        self.stdout.write(f"  - {error}")

                if is_test_data:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"\nAll imported data has been marked as TEST DATA."
                        )
                    )
                    self.stdout.write(
                        f"You can delete this test data later with:"
                    )
                    self.stdout.write(
                        f"python manage.py cleanup_test_data --confirm"
                    )

        except Exception as e:
            raise CommandError(f'Import failed: {e}')
