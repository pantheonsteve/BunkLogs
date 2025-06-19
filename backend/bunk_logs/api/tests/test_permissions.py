from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from bunk_logs.users.models import User
from bunk_logs.bunks.models import Bunk, Unit, Cabin, Session
from bunk_logs.bunklogs.models import BunkLog
from bunk_logs.campers.models import Camper, CamperBunkAssignment

class CounselorPermissionsTest(TestCase):
    def setUp(self):
        # Create test users with different roles
        self.admin = User.objects.create_user(
            email="admin@example.com", 
            password="password123", 
            role="Admin"
        )
        
        self.counselor1 = User.objects.create_user(
            email="counselor1@example.com", 
            password="password123", 
            role="Counselor"
        )
        
        self.counselor2 = User.objects.create_user(
            email="counselor2@example.com", 
            password="password123", 
            role="Counselor"
        )
        
        # Create test data: cabins, sessions, bunks
        self.cabin = Cabin.objects.create(name="Cabin 1", capacity=10)
        self.session = Session.objects.create(
            name="Summer 2025", 
            start_date="2025-06-01", 
            end_date="2025-08-31"
        )
        
        # Create bunk and assign counselor1 to it
        self.bunk = Bunk.objects.create(
            cabin=self.cabin,
            session=self.session,
            is_active=True
        )
        self.bunk.counselors.add(self.counselor1)
        
        # Create a camper and assign to the bunk
        self.camper = Camper.objects.create(
            first_name="Test",
            last_name="Camper"
        )
        
        self.assignment = CamperBunkAssignment.objects.create(
            camper=self.camper,
            bunk=self.bunk,
            is_active=True
        )
        
        # Create API client
        self.client = APIClient()
        
    def test_counselor_can_access_own_bunk(self):
        """Test that a counselor can access their own bunk's data"""
        self.client.force_authenticate(user=self.counselor1)
        url = reverse('bunklog-by-date', kwargs={'bunk_id': self.bunk.id, 'date': '2025-06-15'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_counselor_cannot_access_other_bunk(self):
        """Test that a counselor cannot access another bunk's data"""
        self.client.force_authenticate(user=self.counselor2)
        url = reverse('bunklog-by-date', kwargs={'bunk_id': self.bunk.id, 'date': '2025-06-15'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_admin_can_access_any_bunk(self):
        """Test that an admin can access any bunk's data"""
        self.client.force_authenticate(user=self.admin)
        url = reverse('bunklog-by-date', kwargs={'bunk_id': self.bunk.id, 'date': '2025-06-15'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_counselor_can_create_log_for_own_bunk(self):
        """Test that a counselor can create a log for their own bunk"""
        self.client.force_authenticate(user=self.counselor1)
        url = reverse('bunklog-list')  # Assuming you have a named URL pattern
        data = {
            "date": "2025-06-15",
            "bunk_assignment": self.assignment.id,
            "not_on_camp": False,
            "social_score": 4,
            "behavior_score": 5,
            "participation_score": 3,
            "request_camper_care_help": False,
            "request_unit_head_help": False,
            "description": "Test log entry"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_counselor_cannot_create_log_for_other_bunk(self):
        """Test that a counselor cannot create a log for another bunk"""
        self.client.force_authenticate(user=self.counselor2)
        url = reverse('bunklog-list')
        data = {
            "date": "2025-06-15",
            "bunk_assignment": self.assignment.id,
            "not_on_camp": False,
            "social_score": 4,
            "behavior_score": 5,
            "participation_score": 3,
            "request_camper_care_help": False,
            "request_unit_head_help": False,
            "description": "Test log entry"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)