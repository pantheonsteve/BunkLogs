import unittest
from django.test import TestCase
from django.utils import timezone
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from bunk_logs.messaging.services.report_service import DailyReportService
from bunk_logs.messaging.services.template_service import EmailTemplateService
from bunk_logs.messaging.services.email_service import DevelopmentEmailService, MailgunEmailService
from bunk_logs.messaging.models import EmailTemplate, EmailRecipientGroup, EmailRecipient, EmailLog
from bunk_logs.orders.models import Order, OrderType, OrderItem, Item, ItemCategory
from bunk_logs.bunks.models import Bunk
from django.contrib.auth import get_user_model

User = get_user_model()


class DailyReportServiceTest(TestCase):
    def setUp(self):
        # Create test data
        self.user = User.objects.create_user(username='testuser', email='test@example.com')
        self.bunk = Bunk.objects.create(name='Test Bunk')
        self.order_type = OrderType.objects.create(
            type_name='Maintenance Request',
            type_description='Test maintenance requests'
        )
        self.item_category = ItemCategory.objects.create(
            category_name='Test Category',
            category_description='Test category'
        )
        self.item = Item.objects.create(
            item_name='Test Item',
            item_description='Test item',
            item_category=self.item_category
        )
        
    def test_generate_daily_report_data(self):
        """Test generating daily report data"""
        # Create test order
        order = Order.objects.create(
            user=self.user,
            order_bunk=self.bunk,
            order_type=self.order_type,
            additional_notes='Test notes'
        )
        OrderItem.objects.create(order=order, item=self.item, item_quantity=2)
        
        service = DailyReportService()
        report_data = service.generate_daily_report_data(timezone.now().date())
        
        self.assertEqual(report_data['total_orders'], 1)
        self.assertTrue(report_data['has_orders'])
        self.assertEqual(len(report_data['bunks_with_orders']), 1)


class EmailTemplateServiceTest(TestCase):
    def test_render_daily_orders_email(self):
        """Test rendering daily orders email"""
        service = EmailTemplateService()
        
        # Mock report data
        report_data = {
            'date': timezone.now().date(),
            'total_orders': 2,
            'maintenance_count': 1,
            'camper_care_count': 1,
            'bunks_with_orders_count': 2,
            'has_orders': True,
            'maintenance_requests': [],
            'camper_care_requests': [],
        }
        
        email_content = service.render_daily_orders_email(report_data)
        
        self.assertIn('subject', email_content)
        self.assertIn('html_content', email_content)
        self.assertIn('text_content', email_content)
        self.assertIn('Daily Orders Report', email_content['subject'])


class DevelopmentEmailServiceTest(TestCase):
    def test_send_email(self):
        """Test development email service"""
        service = DevelopmentEmailService()
        
        result = service.send_email(
            recipients=['test@example.com'],
            subject='Test Subject',
            html_content='<p>Test HTML</p>',
            text_content='Test Text'
        )
        
        self.assertTrue(result)
        
        # Check that log was created
        log = EmailLog.objects.first()
        self.assertIsNotNone(log)
        self.assertEqual(log.recipient_email, 'test@example.com')
        self.assertEqual(log.subject, 'Test Subject')
        self.assertTrue(log.success)


class EmailModelTest(TestCase):
    def test_email_template_creation(self):
        """Test creating email template"""
        template = EmailTemplate.objects.create(
            name='test-template',
            subject_template='Test Subject: {{ date }}',
            html_template='<p>Hello {{ name }}</p>',
            text_template='Hello {{ name }}'
        )
        
        self.assertEqual(str(template), 'test-template')
        self.assertTrue(template.is_active)
    
    def test_email_recipient_group_creation(self):
        """Test creating email recipient group"""
        group = EmailRecipientGroup.objects.create(
            name='test-group',
            description='Test group'
        )
        
        recipient = EmailRecipient.objects.create(
            email='test@example.com',
            name='Test User',
            group=group
        )
        
        self.assertEqual(str(group), 'test-group')
        self.assertEqual(str(recipient), 'Test User <test@example.com>')
        self.assertEqual(group.recipients.count(), 1)
