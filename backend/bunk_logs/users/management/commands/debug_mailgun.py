# Create this temporary management command to debug
# backend/bunk_logs/users/management/commands/debug_mailgun.py

from django.core.management.base import BaseCommand
from django.conf import settings
import os

class Command(BaseCommand):
    help = 'Debug Mailgun configuration'

    def handle(self, *args, **options):
        self.stdout.write("=== Mailgun Configuration Debug ===")
        
        # Check environment variables
        self.stdout.write("\n1. Environment Variables:")
        mailgun_api_key = os.environ.get('MAILGUN_API_KEY', 'NOT SET')
        mailgun_domain = os.environ.get('MAILGUN_DOMAIN', 'NOT SET')
        mailgun_api_url = os.environ.get('MAILGUN_API_URL', 'NOT SET')
        
        self.stdout.write(f"MAILGUN_API_KEY: {'***' + mailgun_api_key[-4:] if mailgun_api_key != 'NOT SET' else 'NOT SET'}")
        self.stdout.write(f"MAILGUN_DOMAIN: {mailgun_domain}")
        self.stdout.write(f"MAILGUN_API_URL: {mailgun_api_url}")
        
        # Check Django settings
        self.stdout.write("\n2. Django Settings:")
        try:
            anymail_settings = getattr(settings, 'ANYMAIL', {})
            self.stdout.write(f"ANYMAIL settings: {anymail_settings}")
            self.stdout.write(f"EMAIL_BACKEND: {getattr(settings, 'EMAIL_BACKEND', 'NOT SET')}")
            self.stdout.write(f"DEFAULT_FROM_EMAIL: {getattr(settings, 'DEFAULT_FROM_EMAIL', 'NOT SET')}")
        except Exception as e:
            self.stdout.write(f"Error accessing settings: {e}")
        
        # Check if domain is properly configured
        self.stdout.write("\n3. Domain Configuration:")
        if mailgun_domain and mailgun_domain != 'NOT SET':
            if not mailgun_domain.startswith('mail.'):
                self.stdout.write(self.style.WARNING(
                    f"Domain '{mailgun_domain}' should probably be 'mail.bunklogs.net'"
                ))
            else:
                self.stdout.write(f"Domain looks correct: {mailgun_domain}")
        
        # Check API key format
        self.stdout.write("\n4. API Key Format:")
        if mailgun_api_key and mailgun_api_key != 'NOT SET':
            if not mailgun_api_key.startswith('key-'):
                self.stdout.write(self.style.WARNING(
                    "API key should start with 'key-'"
                ))
            else:
                self.stdout.write("API key format looks correct")
        
        self.stdout.write("\n=== End Debug Info ===")