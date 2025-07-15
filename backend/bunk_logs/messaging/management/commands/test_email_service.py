from django.core.management.base import BaseCommand
from bunk_logs.messaging.services.email_service import get_email_service


class Command(BaseCommand):
    help = 'Test email service configuration and send a test email'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--to',
            type=str,
            required=True,
            help='Email address to send test email to',
        )
        parser.add_argument(
            '--subject',
            type=str,
            default='BunkLogs Email Service Test',
            help='Subject for test email',
        )
    
    def handle(self, *args, **options):
        self.stdout.write('Testing email service configuration...')
        
        email_service = get_email_service()
        
        # Test connection (for Mailgun service)
        if hasattr(email_service, 'test_connection'):
            if email_service.test_connection():
                self.stdout.write(self.style.SUCCESS('✓ Email service connection test passed'))
            else:
                self.stdout.write(self.style.ERROR('✗ Email service connection test failed'))
                return
        
        # Send test email
        subject = options['subject']
        html_content = """
        <html>
        <body>
            <h1>Email Service Test</h1>
            <p>This is a test email from BunkLogs messaging system.</p>
            <p>If you received this email, the email service is working correctly!</p>
            <hr>
            <p><small>Sent from BunkLogs Email Service</small></p>
        </body>
        </html>
        """
        
        text_content = """
        Email Service Test
        ==================
        
        This is a test email from BunkLogs messaging system.
        If you received this email, the email service is working correctly!
        
        ---
        Sent from BunkLogs Email Service
        """
        
        try:
            success = email_service.send_email(
                recipients=[options['to']],
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )
            
            if success:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Test email sent successfully to {options["to"]}')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'✗ Failed to send test email to {options["to"]}')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Error sending test email: {str(e)}')
            )
