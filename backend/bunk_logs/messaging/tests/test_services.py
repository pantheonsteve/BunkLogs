
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from bunk_logs.bunks.models import Bunk
from bunk_logs.messaging.models import EmailLog
from bunk_logs.messaging.models import EmailRecipient
from bunk_logs.messaging.models import EmailRecipientGroup
from bunk_logs.messaging.models import EmailTemplate
from bunk_logs.messaging.services.email_service import DevelopmentEmailService
from bunk_logs.messaging.services.report_service import DailyReportService
from bunk_logs.messaging.services.template_service import EmailTemplateService
from bunk_logs.orders.models import Item
from bunk_logs.orders.models import ItemCategory
from bunk_logs.orders.models import Order
from bunk_logs.orders.models import OrderItem
from bunk_logs.orders.models import OrderType

User = get_user_model()


class DailyReportServiceTest(TestCase):
    def setUp(self):
        # Create test data
        self.user = User.objects.create_user(username="testuser", email="test@example.com")
        self.bunk = Bunk.objects.create(name="Test Bunk")
        self.order_type = OrderType.objects.create(
            type_name="Maintenance Request",
            type_description="Test maintenance requests",
        )
        self.item_category = ItemCategory.objects.create(
            category_name="Test Category",
            category_description="Test category",
        )
        self.item = Item.objects.create(
            item_name="Test Item",
            item_description="Test item",
            item_category=self.item_category,
        )

    def test_generate_daily_report_data(self):
        """Test generating daily report data"""
        # Create test order
        order = Order.objects.create(
            user=self.user,
            order_bunk=self.bunk,
            order_type=self.order_type,
            additional_notes="Test notes",
        )
        OrderItem.objects.create(order=order, item=self.item, item_quantity=2)

        service = DailyReportService()
        report_data = service.generate_daily_report_data(timezone.now().date())

        assert report_data["total_orders"] == 1
        assert report_data["has_orders"]
        assert len(report_data["bunks_with_orders"]) == 1


class EmailTemplateServiceTest(TestCase):
    def test_render_daily_orders_email(self):
        """Test rendering daily orders email"""
        service = EmailTemplateService()

        # Mock report data
        report_data = {
            "date": timezone.now().date(),
            "total_orders": 2,
            "maintenance_count": 1,
            "camper_care_count": 1,
            "bunks_with_orders_count": 2,
            "has_orders": True,
            "maintenance_requests": [],
            "camper_care_requests": [],
        }

        email_content = service.render_daily_orders_email(report_data)

        assert "subject" in email_content
        assert "html_content" in email_content
        assert "text_content" in email_content
        assert "Daily Orders Report" in email_content["subject"]


class DevelopmentEmailServiceTest(TestCase):
    def test_send_email(self):
        """Test development email service"""
        service = DevelopmentEmailService()

        result = service.send_email(
            recipients=["test@example.com"],
            subject="Test Subject",
            html_content="<p>Test HTML</p>",
            text_content="Test Text",
        )

        assert result

        # Check that log was created
        log = EmailLog.objects.first()
        assert log is not None
        assert log.recipient_email == "test@example.com"
        assert log.subject == "Test Subject"
        assert log.success


class EmailModelTest(TestCase):
    def test_email_template_creation(self):
        """Test creating email template"""
        template = EmailTemplate.objects.create(
            name="test-template",
            subject_template="Test Subject: {{ date }}",
            html_template="<p>Hello {{ name }}</p>",
            text_template="Hello {{ name }}",
        )

        assert str(template) == "test-template"
        assert template.is_active

    def test_email_recipient_group_creation(self):
        """Test creating email recipient group"""
        group = EmailRecipientGroup.objects.create(
            name="test-group",
            description="Test group",
        )

        recipient = EmailRecipient.objects.create(
            email="test@example.com",
            name="Test User",
            group=group,
        )

        assert str(group) == "test-group"
        assert str(recipient) == "Test User <test@example.com>"
        assert group.recipients.count() == 1
