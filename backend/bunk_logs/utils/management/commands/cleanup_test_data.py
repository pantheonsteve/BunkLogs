"""
Django management command to clean up test data.

This command allows you to easily delete all dummy/testing data
that has been imported or created with the is_test_data flag set to True.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.apps import apps

from bunk_logs.utils.models import TestDataMixin


class Command(BaseCommand):
    help = 'Delete all test data from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Actually delete the data (without this flag, only shows what would be deleted)',
        )
        parser.add_argument(
            '--app',
            type=str,
            help='Only delete test data from specific app (e.g. "users", "campers", "orders")',
        )
        parser.add_argument(
            '--model',
            type=str,
            help='Only delete test data from specific model (e.g. "User", "Camper", "Order")',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING(
                "Scanning for test data across all models..."
            )
        )

        # Get all models that inherit from TestDataMixin
        test_data_models = []
        for app_config in apps.get_app_configs():
            if options['app'] and app_config.label != options['app']:
                continue
                
            for model in app_config.get_models():
                if issubclass(model, TestDataMixin):
                    if options['model'] and model.__name__ != options['model']:
                        continue
                    test_data_models.append(model)

        if not test_data_models:
            self.stdout.write(
                self.style.ERROR(
                    "No models found that inherit from TestDataMixin"
                )
            )
            return

        # Count test data in each model
        total_test_records = 0
        model_counts = {}
        
        for model in test_data_models:
            count = model.get_test_data_queryset().count()
            if count > 0:
                model_counts[model] = count
                total_test_records += count

        if total_test_records == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    "No test data found in the database!"
                )
            )
            return

        # Display what would be deleted
        self.stdout.write(
            self.style.WARNING(
                f"\nFound {total_test_records} test data records across {len(model_counts)} models:"
            )
        )
        
        for model, count in model_counts.items():
            app_label = model._meta.app_label
            model_name = model.__name__
            self.stdout.write(f"  - {app_label}.{model_name}: {count} records")

        if not options['confirm']:
            self.stdout.write(
                self.style.WARNING(
                    "\nThis is a dry run. Use --confirm to actually delete the data."
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    "Command to actually delete: python manage.py cleanup_test_data --confirm"
                )
            )
            return

        # Confirm deletion
        self.stdout.write(
            self.style.ERROR(
                f"\nAre you sure you want to delete {total_test_records} test data records?"
            )
        )
        
        confirm = input("Type 'yes' to confirm deletion: ")
        if confirm.lower() != 'yes':
            self.stdout.write("Deletion cancelled.")
            return

        # Delete the data
        self.stdout.write("Deleting test data...")
        
        total_deleted = 0
        with transaction.atomic():
            # Delete in reverse dependency order to avoid foreign key constraints
            # OrderItem -> Order -> OrderType, Item -> ItemCategory
            # BunkLog -> CamperBunkAssignment -> Camper
            # Bunk -> Unit, Session, Cabin
            # User
            
            deletion_order = [
                'BunkLog',
                'OrderItem', 
                'Order',
                'CamperBunkAssignment',
                'Bunk',
                'Camper',
                'Item',
                'OrderType',
                'BunkLogsOrderTypeItemCategory',
                'ItemCategory',
                'Unit',
                'Session', 
                'Cabin',
                'User',
            ]
            
            for model_name in deletion_order:
                for model in model_counts.keys():
                    if model.__name__ == model_name:
                        deleted_count = model.delete_all_test_data()
                        if deleted_count > 0:
                            total_deleted += deleted_count
                            app_label = model._meta.app_label
                            self.stdout.write(
                                f"  Deleted {deleted_count} {app_label}.{model_name} records"
                            )
                        break

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSuccessfully deleted {total_deleted} test data records!"
            )
        )
