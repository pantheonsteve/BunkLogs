"""
Django management command to test the UnitStaffAssignment endpoint.
Run with: python manage.py test_staff_assignment_endpoint --user-id 1
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from bunk_logs.bunks.models import UnitStaffAssignment
from bunk_logs.api.serializers import UnitStaffAssignmentSerializer
import json

User = get_user_model()

class Command(BaseCommand):
    help = 'Test the UnitStaffAssignment endpoint to verify it returns start_date and end_date'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='User ID to test with',
            default=None
        )
        parser.add_argument(
            '--list-users',
            action='store_true',
            help='List available users with staff assignments',
        )

    def handle(self, *args, **options):
        if options['list_users']:
            self.list_users_with_assignments()
            return

        user_id = options['user_id']
        if not user_id:
            self.stdout.write(
                self.style.ERROR('Please provide --user-id or use --list-users to see available options')
            )
            return

        try:
            # Try to get the assignment using the same logic as the viewset
            assignment = UnitStaffAssignment.objects.select_related('unit', 'staff_member').get(
                staff_member__id=user_id
            )
            
            # Serialize the assignment
            serializer = UnitStaffAssignmentSerializer(assignment)
            data = serializer.data
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Found assignment for user ID {user_id}')
            )
            
            # Pretty print the response
            self.stdout.write("Response data:")
            self.stdout.write(json.dumps(data, indent=2, default=str))
            
            # Check for required fields
            required_fields = ['start_date', 'end_date', 'staff_member_details']
            missing_fields = []
            
            for field in required_fields:
                if field not in data:
                    missing_fields.append(field)
            
            if missing_fields:
                self.stdout.write(
                    self.style.ERROR(f"❌ Missing required fields: {missing_fields}")
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS("✅ All required fields are present!")
                )
                
                # Check staff_member_details for user ID
                if 'staff_member_details' in data and 'id' in data['staff_member_details']:
                    self.stdout.write(
                        self.style.SUCCESS(f"✅ staff_member_details contains canonical user ID: {data['staff_member_details']['id']}")
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR("❌ staff_member_details missing canonical user ID")
                    )
                    
                # Check date fields
                start_date = data.get('start_date', 'N/A')
                end_date = data.get('end_date', 'ongoing')
                self.stdout.write(f"📅 Assignment dates: {start_date} to {end_date}")
                
        except UnitStaffAssignment.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'❌ No UnitStaffAssignment found for user ID {user_id}')
            )
            self.stdout.write("Available users with staff assignments:")
            self.list_users_with_assignments()
            
        except UnitStaffAssignment.MultipleObjectsReturned:
            self.stdout.write(
                self.style.WARNING(f'⚠️  Multiple assignments found for user ID {user_id}')
            )
            # Get the latest one (same logic as viewset)
            assignment = UnitStaffAssignment.objects.select_related('unit', 'staff_member').filter(
                staff_member__id=user_id
            ).order_by('-start_date').first()
            
            if assignment:
                serializer = UnitStaffAssignmentSerializer(assignment)
                data = serializer.data
                self.stdout.write("Using latest assignment:")
                self.stdout.write(json.dumps(data, indent=2, default=str))
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error: {str(e)}')
            )

    def list_users_with_assignments(self):
        """List users who have staff assignments."""
        assignments = UnitStaffAssignment.objects.select_related('staff_member', 'unit').all()
        
        if not assignments:
            self.stdout.write("No staff assignments found in the database.")
            return
            
        self.stdout.write("\nUsers with staff assignments:")
        self.stdout.write("-" * 60)
        
        for assignment in assignments:
            user = assignment.staff_member
            self.stdout.write(
                f"User ID: {user.id} | {user.first_name} {user.last_name} ({user.email}) | "
                f"Role: {assignment.role} | Unit: {assignment.unit.name} | "
                f"Dates: {assignment.start_date} to {assignment.end_date or 'ongoing'}"
            )
