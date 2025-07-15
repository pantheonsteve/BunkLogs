from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
import logging

from bunk_logs.messaging.services.report_service import DailyReportService
from bunk_logs.messaging.services.template_service import EmailTemplateService
from bunk_logs.messaging.services.email_service import get_email_service
from bunk_logs.messaging.models import EmailSchedule

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send daily orders report email'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Date to send report for (YYYY-MM-DD format). Defaults to yesterday.',
        )
        parser.add_argument(
            '--recipients',
            type=str,
            nargs='+',
            help='Email addresses to send to (overrides configured recipients)',
        )
        parser.add_argument(
            '--group',
            type=str,
            help='Email recipient group to send to (default: daily-reports)',
            default='daily-reports'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending',
        )
    
    def handle(self, *args, **options):
        # Parse date
        if options['date']:
            try:
                target_date = date.fromisoformat(options['date'])
            except ValueError:
                self.stdout.write(self.style.ERROR('Invalid date format. Use YYYY-MM-DD'))
                return
        else:
            # Default to yesterday
            target_date = timezone.now().date() - timedelta(days=1)
        
        self.stdout.write(f'Generating daily report for {target_date}...')
        
        # Generate report data
        try:
            report_service = DailyReportService()
            report_data = report_service.generate_daily_report_data(target_date)
            
            self.stdout.write(
                f'Found {report_data["total_orders"]} orders '
                f'({report_data["maintenance_count"]} maintenance, '
                f'{report_data["camper_care_count"]} camper care)'
            )
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error generating report data: {str(e)}'))
            logger.error(f'Error generating report data: {str(e)}', exc_info=True)
            return
        
        # Render email template
        try:
            template_service = EmailTemplateService()
            email_content = template_service.render_daily_orders_email(report_data)
            
            self.stdout.write(f'Generated email with subject: "{email_content["subject"]}"')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error rendering email template: {str(e)}'))
            logger.error(f'Error rendering email template: {str(e)}', exc_info=True)
            return
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('DRY RUN - Email would be sent with:'))
            self.stdout.write(f'Subject: {email_content["subject"]}')
            if options['recipients']:
                self.stdout.write(f'Recipients: {", ".join(options["recipients"])}')
            else:
                self.stdout.write(f'Group: {options["group"]}')
            self.stdout.write('--- TEXT CONTENT ---')
            self.stdout.write(email_content['text_content'])
            return
        
        # Send email
        try:
            email_service = get_email_service()
            
            if options['recipients']:
                # Send to specific recipients
                success = email_service.send_daily_report(
                    recipients=options['recipients'],
                    **email_content
                )
                recipient_info = f"recipients: {', '.join(options['recipients'])}"
            else:
                # Send to group
                success = email_service.send_to_group(
                    group_name=options['group'],
                    template_name='daily_report',
                    **email_content
                )
                recipient_info = f"group: {options['group']}"
            
            if success:
                self.stdout.write(
                    self.style.SUCCESS(f'Daily report sent successfully to {recipient_info}')
                )
                
                # Update last_sent for scheduled emails
                EmailSchedule.objects.filter(
                    name='daily-orders-report',
                    is_active=True
                ).update(last_sent=timezone.now())
                
            else:
                self.stdout.write(
                    self.style.ERROR(f'Failed to send daily report to {recipient_info}')
                )
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error sending email: {str(e)}'))
            logger.error(f'Error sending daily report email: {str(e)}', exc_info=True)
