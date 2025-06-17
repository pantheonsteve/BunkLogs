"""
Django management command to create sample test data for demonstration.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from bunk_logs.users.models import User
from bunk_logs.campers.models import Camper
from bunk_logs.bunks.models import Cabin, Session, Unit, Bunk


class Command(BaseCommand):
    help = 'Create sample test data to demonstrate the test data management system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete-existing',
            action='store_true',
            help='Delete any existing test data before creating new test data',
        )

    def handle(self, *args, **options):
        if options['delete_existing']:
            self.stdout.write("Deleting existing test data...")
            
            # Delete in dependency order
            deleted_counts = {
                'User': User.delete_all_test_data(),
                'Camper': Camper.delete_all_test_data(),
                'Bunk': Bunk.delete_all_test_data(),
                'Unit': Unit.delete_all_test_data(), 
                'Session': Session.delete_all_test_data(),
                'Cabin': Cabin.delete_all_test_data(),
            }
            
            for model_name, count in deleted_counts.items():
                if count > 0:
                    self.stdout.write(f"  Deleted {count} {model_name} test records")
        
        self.stdout.write("Creating sample test data...")
        
        with transaction.atomic():
            # Create test users
            test_user = User.objects.create_user(
                email='test.counselor@example.com',
                password='testpass123',
                first_name='Test',
                last_name='Counselor',
                role=User.COUNSELOR,
                is_test_data=True
            )
            
            test_unit_head = User.objects.create_user(
                email='test.unithead@example.com',
                password='testpass123',
                first_name='Test',
                last_name='Unit Head',
                role=User.UNIT_HEAD,
                is_test_data=True
            )
            
            # Create test cabin
            test_cabin = Cabin.objects.create(
                name='Test Cabin A',
                capacity=10,
                location='Test Area',
                notes='This is test cabin data',
                is_test_data=True
            )
            
            # Create test session
            test_session = Session.objects.create(
                name='Test Summer Session 2025',
                start_date='2025-06-15',
                end_date='2025-08-15',
                is_active=True,
                is_test_data=True
            )
            
            # Create test unit
            test_unit = Unit.objects.create(
                name='Test Unit Alpha',
                unit_head=test_unit_head,
                is_test_data=True
            )
            
            # Create test bunk
            test_bunk = Bunk.objects.create(
                cabin=test_cabin,
                session=test_session,
                unit=test_unit,
                is_active=True,
                is_test_data=True
            )
            test_bunk.counselors.add(test_user)
            
            # Create test campers
            for i in range(3):
                Camper.objects.create(
                    first_name=f'Test Camper {i+1}',
                    last_name='Doe',
                    date_of_birth='2010-01-01',
                    emergency_contact_name='Test Parent',
                    emergency_contact_phone='555-0123',
                    camper_notes=f'This is test camper #{i+1}',
                    is_test_data=True
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                'Successfully created test data!\n'
                'You can now run: python manage.py cleanup_test_data\n'
                'to see the test data detection in action.'
            )
        )
