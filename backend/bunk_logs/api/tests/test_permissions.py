from datetime import date
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from bunk_logs.bunks.models import Bunk
from bunk_logs.bunks.models import Cabin
from bunk_logs.bunks.models import Session
from bunk_logs.campers.models import Camper
from bunk_logs.campers.models import CamperBunkAssignment
from bunk_logs.users.models import User


class CounselorPermissionsTest(TestCase):
    def setUp(self):
        # Create test users with different roles
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="password123",
            role="Admin",
        )

        self.counselor1 = User.objects.create_user(
            email="counselor1@example.com",
            password="password123",
            role="Counselor",
        )

        self.counselor2 = User.objects.create_user(
            email="counselor2@example.com",
            password="password123",
            role="Counselor",
        )

        # Create test data: cabins, sessions, bunks
        self.cabin = Cabin.objects.create(name="Cabin 1", capacity=10)
        self.session = Session.objects.create(
            name="Summer Session",
            start_date=date.today() - timedelta(days=30),
            end_date=date.today() + timedelta(days=60),
        )

        # Create bunk and assign counselor1 to it
        self.bunk = Bunk.objects.create(
            cabin=self.cabin,
            session=self.session,
            is_active=True,
        )
        # Use the new assignment method
        self.bunk.assign_counselor(self.counselor1, is_primary=True)

        # Create a camper and assign to the bunk
        self.camper = Camper.objects.create(
            first_name="Test",
            last_name="Camper",
        )

        self.assignment = CamperBunkAssignment.objects.create(
            camper=self.camper,
            bunk=self.bunk,
            start_date=date.today() - timedelta(days=7),
            is_active=True,
        )

        # Create API client
        self.client = APIClient()

    def test_counselor_can_access_own_bunk(self):
        """Test that a counselor can access their own bunk's data"""
        self.client.force_authenticate(user=self.counselor1)
        url = reverse("api:bunklog-by-date", kwargs={"bunk_id": self.bunk.id, "date": "2025-06-15"})
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_counselor_cannot_access_other_bunk(self):
        """Test that a counselor cannot access another bunk's data"""
        self.client.force_authenticate(user=self.counselor2)
        url = reverse("api:bunklog-by-date", kwargs={"bunk_id": self.bunk.id, "date": "2025-06-15"})
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_access_any_bunk(self):
        """Test that an admin can access any bunk's data"""
        self.client.force_authenticate(user=self.admin)
        url = reverse("api:bunklog-by-date", kwargs={"bunk_id": self.bunk.id, "date": "2025-06-15"})
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_counselor_can_create_log_for_own_bunk(self):
        """Test that a counselor can create a log for their own bunk"""
        self.client.force_authenticate(user=self.counselor1)
        url = reverse("api:bunklog-list")
        data = {
            "date": date.today().isoformat(),
            "bunk_assignment": self.assignment.id,
            "not_on_camp": False,
            "social_score": 4,
            "behavior_score": 5,
            "participation_score": 3,
            "request_camper_care_help": False,
            "request_unit_head_help": False,
            "description": "Test log entry",
        }
        response = self.client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED

    def test_counselor_cannot_create_log_for_other_bunk(self):
        """Test that a counselor cannot create a log for another bunk"""
        self.client.force_authenticate(user=self.counselor2)
        url = reverse("api:bunklog-list")
        data = {
            "date": date.today().isoformat(),
            "bunk_assignment": self.assignment.id,
            "not_on_camp": False,
            "social_score": 4,
            "behavior_score": 5,
            "participation_score": 3,
            "request_camper_care_help": False,
            "request_unit_head_help": False,
            "description": "Test log entry",
        }
        response = self.client.post(url, data, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN


class BunkViewSetPermissionsTest(TestCase):
    """
    Verify that BunkViewSet requires authentication.

    AllowAny was previously set here with no rationale. Every real caller
    (BunkCard component, unit-head and camper-care dashboards) operates inside
    an authenticated session, so unauthenticated access is not needed.
    """

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="staff@example.com",
            password="password123",
            role="Counselor",
        )
        cabin = Cabin.objects.create(name="Cabin A", capacity=8)
        session = Session.objects.create(
            name="Summer 2025",
            start_date=date.today() - timedelta(days=30),
            end_date=date.today() + timedelta(days=60),
        )
        self.bunk = Bunk.objects.create(cabin=cabin, session=session, is_active=True)

    def test_unauthenticated_list_returns_401(self):
        url = reverse("api:bunk-list")
        response = self.client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unauthenticated_detail_returns_401(self):
        url = reverse("api:bunk-detail", kwargs={"id": self.bunk.id})
        response = self.client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_list_succeeds(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("api:bunk-list")
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_authenticated_detail_succeeds(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("api:bunk-detail", kwargs={"id": self.bunk.id})
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
