"""
Django management command to test the Camper Care endpoint.
Run with: python manage.py test_campercare_endpoint --user-id 26 --date 2025-06-24
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import models
from bunk_logs.bunks.models import Unit, UnitStaffAssignment
from bunk_logs.api.serializers import CamperCareBunksSerializer
from datetime import datetime
import json

User = get_user_model()

class Command(BaseCommand):
    help = 'Test the Camper Care endpoint to verify it returns unit data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='Camper Care user ID to test with',
            default=26
        )
        parser.add_argument(
            '--date',
            type=str,
            help='Date to test with (YYYY-MM-DD format)',
            default='2025-06-24'
        )

    def handle(self, *args, **options):
        user_id = options['user_id']
        date_str = options['date']
        
        self.stdout.write(f'🧪 Testing Camper Care endpoint for User ID {user_id} on {date_str}')
        
        try:
            # Check if user exists
            user = User.objects.get(id=user_id)
            self.stdout.write(f'✅ Found user: {user.first_name} {user.last_name} ({user.email})')
            self.stdout.write(f'   Role: {user.role}')
            
            # Parse the date
            query_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            
            # Check for staff assignments
            assignments = UnitStaffAssignment.objects.filter(
                staff_member_id=user_id,
                role='camper_care',
                start_date__lte=query_date,
            ).filter(
                models.Q(end_date__isnull=True) | models.Q(end_date__gte=query_date)
            )
            
            self.stdout.write(f'📋 Found {assignments.count()} assignment(s):')
            for assignment in assignments:
                self.stdout.write(f'   - Unit: {assignment.unit.name} (ID: {assignment.unit.id})')
                self.stdout.write(f'     Role: {assignment.role}')
                self.stdout.write(f'     Dates: {assignment.start_date} to {assignment.end_date or "ongoing"}')
            
            # Get units from assignments
            units = Unit.objects.filter(staff_assignments__in=assignments).distinct()
            self.stdout.write(f'🏠 Found {units.count()} unit(s) from assignments:')
            
            if not units.exists():
                self.stdout.write('⚠️  No units found from assignments, checking legacy camper_care_id...')
                legacy_unit = Unit.objects.filter(camper_care_id=user_id).first()
                if legacy_unit:
                    units = [legacy_unit]
                    self.stdout.write(f'✅ Found legacy unit: {legacy_unit.name}')
                else:
                    self.stdout.write('❌ No units found for this camper care team member')
                    return
            
            # Serialize the data
            context = {'date': date_str}
            data = []
            for unit in units:
                self.stdout.write(f'📦 Processing unit: {unit.name}')
                serializer = CamperCareBunksSerializer(unit, context=context)
                unit_data = serializer.data
                data.append(unit_data)
                
                # Show summary
                self.stdout.write(f'   Bunks: {len(unit_data.get("bunks", []))}')
                for bunk in unit_data.get("bunks", []):
                    self.stdout.write(f'     - {bunk.get("name", "Unknown")} (ID: {bunk.get("id", "?")})')
            
            self.stdout.write('✅ Endpoint would return:')
            self.stdout.write(json.dumps(data, indent=2))
            
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ User with ID {user_id} not found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {str(e)}'))
            import traceback
            traceback.print_exc()
