"""Django admin access for Camper Care orders and Maintenance tickets."""
from django.contrib.auth import get_user_model
from django.test import Client
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class CoreOrdersAdminTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpass",
        )
        self.client = Client()
        self.client.login(username="admin@example.com", password="adminpass")

    def test_camper_care_order_admin_access(self):
        url = reverse("admin:core_order_changelist")
        response = self.client.get(url)
        assert response.status_code == 200

    def test_maintenance_ticket_admin_access(self):
        url = reverse("admin:core_maintenanceticket_changelist")
        response = self.client.get(url)
        assert response.status_code == 200

    def test_order_activity_event_admin_access(self):
        url = reverse("admin:core_orderactivityevent_changelist")
        response = self.client.get(url)
        assert response.status_code == 200
