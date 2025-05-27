"""Test admin access to orders models."""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

class OrdersAdminTests(TestCase):
    def setUp(self):
        # Create superuser
        self.superuser = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass',
        )
        self.client = Client()
        self.client.login(username='admin@example.com', password='adminpass')
    
    def test_order_admin_access(self):
        """Test that the order admin page is accessible."""
        url = reverse('admin:orders_order_changelist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_ordertype_admin_access(self):
        """Test that the ordertype admin page is accessible."""
        url = reverse('admin:orders_ordertype_changelist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_item_admin_access(self):
        """Test that the item admin page is accessible."""
        url = reverse('admin:orders_item_changelist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_itemcategory_admin_access(self):
        """Test that the itemcategory admin page is accessible."""
        url = reverse('admin:orders_itemcategory_changelist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
