# backend/bunk_logs/orders/management/commands/send_daily_digest.py
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

from bunk_logs.orders.models import Order

User = get_user_model()

class Command(BaseCommand):
    help = 'Send daily digest of orders to administrators'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Date to generate digest for (YYYY-MM-DD format)',
            default=None
        )

    def handle(self, *args, **options):
        # Get date (yesterday by default)
        if options['date']:
            from datetime import datetime
            target_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
        else:
            target_date = (timezone.now() - timedelta(days=1)).date()

        # Get orders for the target date
        orders = Order.objects.filter(
            order_date__date=target_date
        ).select_related('user', 'order_bunk', 'order_type').prefetch_related('order_items__item')

        if not orders.exists():
            self.stdout.write(f'No orders found for {target_date}')
            return

        # Prepare digest data
        digest_data = {
            'date': target_date,
            'total_orders': orders.count(),
            'orders_by_status': {},
            'orders_by_type': {},
            'recent_orders': orders.order_by('-order_date')[:10],
        }

        # Group by status
        for status_choice in Order._meta.get_field('order_status').choices:
            status_code = status_choice[0]
            status_name = status_choice[1]
            count = orders.filter(order_status=status_code).count()
            if count > 0:
                digest_data['orders_by_status'][status_name] = count

        # Group by type
        from django.db.models import Count
        order_types = orders.values('order_type__type_name').annotate(
            count=Count('id')
        ).order_by('-count')
        
        for ot in order_types:
            digest_data['orders_by_type'][ot['order_type__type_name']] = ot['count']

        # Get admin users to send to
        admin_users = User.objects.filter(
            is_staff=True, 
            is_active=True
        ).exclude(email='')

        if not admin_users.exists():
            self.stdout.write('No admin users found to send digest to')
            return

        # Send email to each admin
        subject = f'Daily Order Digest - {target_date.strftime("%B %d, %Y")}'
        
        # Create email content
        email_content = self.format_digest_content(digest_data)
        
        for admin in admin_users:
            try:
                send_mail(
                    subject=subject,
                    message=email_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[admin.email],
                    fail_silently=False,
                )
                self.stdout.write(f'Digest sent to {admin.email}')
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Failed to send digest to {admin.email}: {str(e)}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Daily digest sent for {target_date}')
        )

    def format_digest_content(self, data):
        """Format the digest content as plain text"""
        content = f"""
Daily Order Digest - {data['date'].strftime('%B %d, %Y')}
========================================

Summary:
- Total Orders: {data['total_orders']}

Orders by Status:
"""
        for status, count in data['orders_by_status'].items():
            content += f"- {status}: {count}\n"

        content += "\nOrders by Type:\n"
        for order_type, count in data['orders_by_type'].items():
            content += f"- {order_type}: {count}\n"

        content += "\nRecent Orders:\n"
        for order in data['recent_orders']:
            content += f"- Order #{order.id} - {order.user.email} - {order.order_status} - {order.order_type.type_name}\n"

        content += f"\nView all orders: {settings.FRONTEND_URL}/admin/orders/order/\n"
        content += f"\nBunk Logs Administration\n{settings.FRONTEND_URL}"

        return content