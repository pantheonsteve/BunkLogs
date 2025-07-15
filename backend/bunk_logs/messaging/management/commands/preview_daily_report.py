from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
import webbrowser
import tempfile
import os

from bunk_logs.messaging.services.report_service import DailyReportService
from bunk_logs.messaging.services.template_service import EmailTemplateService


class Command(BaseCommand):
    help = 'Preview daily orders report email in browser'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Date to preview (YYYY-MM-DD format). Defaults to today.',
        )
        parser.add_argument(
            '--open-browser',
            action='store_true',
            help='Automatically open preview in browser',
        )
        parser.add_argument(
            '--save-to',
            type=str,
            help='Save HTML to specific file path instead of temp file',
        )
        parser.add_argument(
            '--format',
            choices=['html', 'text', 'both'],
            default='html',
            help='Output format to display/save',
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
            target_date = timezone.now().date()
        
        self.stdout.write(f'Generating preview for {target_date}...')
        
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
            return
        
        # Render template
        try:
            template_service = EmailTemplateService()
            email_content = template_service.render_daily_orders_email(report_data)
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error rendering email template: {str(e)}'))
            return
        
        # Output subject
        self.stdout.write(f'Subject: {email_content["subject"]}')
        
        # Handle different output formats
        if options['format'] in ['text', 'both']:
            self.stdout.write('\n--- TEXT VERSION ---')
            self.stdout.write(email_content['text_content'])
        
        if options['format'] in ['html', 'both']:
            # Save HTML content
            if options['save_to']:
                html_path = options['save_to']
                if not html_path.endswith('.html'):
                    html_path += '.html'
            else:
                # Create temporary file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                    html_path = f.name
            
            try:
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(email_content['html_content'])
                
                self.stdout.write(self.style.SUCCESS(f'HTML preview saved to: {html_path}'))
                
                if options['open_browser']:
                    # Open in browser
                    webbrowser.open(f'file://{os.path.abspath(html_path)}')
                    self.stdout.write(self.style.SUCCESS('Opened in browser'))
                else:
                    self.stdout.write(f'To view in browser, run: open "{html_path}"')
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error saving HTML file: {str(e)}'))
        
        # Show statistics
        self.stdout.write('\n--- REPORT STATISTICS ---')
        self.stdout.write(f'Report Date: {target_date}')
        self.stdout.write(f'Total Orders: {report_data["total_orders"]}')
        self.stdout.write(f'Maintenance Requests: {report_data["maintenance_count"]}')
        self.stdout.write(f'Camper Care Requests: {report_data["camper_care_count"]}')
        self.stdout.write(f'Bunks with Orders: {report_data["bunks_with_orders_count"]}')
        
        if report_data["bunks_with_orders"]:
            bunk_names = [bunk.name for bunk in report_data["bunks_with_orders"]]
            self.stdout.write(f'Affected Bunks: {", ".join(bunk_names)}')
        
        # Show order status breakdown
        if report_data["orders_by_status"]:
            self.stdout.write('\n--- ORDER STATUS BREAKDOWN ---')
            for status, orders in report_data["orders_by_status"].items():
                self.stdout.write(f'{status.title()}: {len(orders)}')
