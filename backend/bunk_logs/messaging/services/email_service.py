import requests
import logging
from django.conf import settings
from typing import List, Dict, Any, Optional

from ..models import EmailLog, EmailRecipient, EmailRecipientGroup

logger = logging.getLogger(__name__)


class MailgunEmailService:
    """Service for sending emails via Mailgun API"""
    
    def __init__(self):
        self.api_key = getattr(settings, 'MAILGUN_API_KEY', None)
        self.domain = getattr(settings, 'MAILGUN_DOMAIN', None)
        self.from_email = getattr(settings, 'MAILGUN_FROM_EMAIL', f'reports@{self.domain}')
        self.base_url = f"https://api.mailgun.net/v3/{self.domain}" if self.domain else None
        
        if not self.api_key or not self.domain:
            logger.warning("Mailgun API key or domain not configured. Email sending will be disabled.")
    
    def send_email(
        self, 
        recipients: List[str], 
        subject: str, 
        html_content: str, 
        text_content: str,
        template_name: Optional[str] = None
    ) -> bool:
        """Send email to multiple recipients"""
        
        if not self.api_key or not self.domain:
            logger.error("Mailgun not configured. Cannot send email.")
            return False
        
        success_count = 0
        
        for recipient in recipients:
            if self._send_single_email(recipient, subject, html_content, text_content, template_name):
                success_count += 1
        
        logger.info(f"Sent email to {success_count}/{len(recipients)} recipients")
        return success_count == len(recipients)
    
    def send_daily_report(
        self, 
        recipients: List[str], 
        subject: str, 
        html_content: str, 
        text_content: str
    ) -> bool:
        """Send daily report email"""
        return self.send_email(recipients, subject, html_content, text_content, "daily_report")
    
    def send_to_group(
        self, 
        group_name: str, 
        subject: str, 
        html_content: str, 
        text_content: str,
        template_name: Optional[str] = None
    ) -> bool:
        """Send email to all active recipients in a group"""
        
        try:
            group = EmailRecipientGroup.objects.get(name=group_name, is_active=True)
            recipients = group.recipients.filter(is_active=True).values_list('email', flat=True)
            
            if not recipients:
                logger.warning(f"No active recipients found in group '{group_name}'")
                return False
            
            return self.send_email(list(recipients), subject, html_content, text_content, template_name)
            
        except EmailRecipientGroup.DoesNotExist:
            logger.error(f"Email recipient group '{group_name}' not found or inactive")
            return False
    
    def _send_single_email(
        self, 
        recipient: str, 
        subject: str, 
        html_content: str, 
        text_content: str,
        template_name: Optional[str] = None
    ) -> bool:
        """Send email to a single recipient"""
        
        try:
            response = requests.post(
                f"{self.base_url}/messages",
                auth=("api", self.api_key),
                data={
                    "from": self.from_email,
                    "to": recipient,
                    "subject": subject,
                    "text": text_content,
                    "html": html_content
                },
                timeout=30
            )
            
            success = response.status_code == 200
            
            # Log the email attempt
            EmailLog.objects.create(
                recipient_email=recipient,
                subject=subject,
                success=success,
                error_message="" if success else f"HTTP {response.status_code}: {response.text}",
                mailgun_message_id=response.json().get('id', '') if success else ""
            )
            
            if success:
                logger.info(f"Email sent successfully to {recipient}")
            else:
                logger.error(f"Failed to send email to {recipient}: {response.status_code} {response.text}")
            
            return success
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error sending email to {recipient}: {str(e)}")
            
            # Log the error
            EmailLog.objects.create(
                recipient_email=recipient,
                subject=subject,
                success=False,
                error_message=f"Network error: {str(e)}"
            )
            
            return False
        
        except Exception as e:
            logger.error(f"Unexpected error sending email to {recipient}: {str(e)}")
            
            # Log the error
            EmailLog.objects.create(
                recipient_email=recipient,
                subject=subject,
                success=False,
                error_message=f"Unexpected error: {str(e)}"
            )
            
            return False
    
    def test_connection(self) -> bool:
        """Test the Mailgun connection"""
        
        if not self.api_key or not self.domain:
            return False
        
        try:
            response = requests.get(
                f"{self.base_url}/domains/{self.domain}",
                auth=("api", self.api_key),
                timeout=10
            )
            return response.status_code == 200
            
        except requests.exceptions.RequestException:
            return False


class DevelopmentEmailService:
    """Email service for development that logs instead of sending"""
    
    def send_email(
        self, 
        recipients: List[str], 
        subject: str, 
        html_content: str, 
        text_content: str,
        template_name: Optional[str] = None
    ) -> bool:
        """Log email instead of sending in development"""
        
        logger.info("=" * 50)
        logger.info("DEVELOPMENT EMAIL")
        logger.info("=" * 50)
        logger.info(f"To: {', '.join(recipients)}")
        logger.info(f"Subject: {subject}")
        logger.info(f"Template: {template_name or 'N/A'}")
        logger.info("-" * 50)
        logger.info("TEXT CONTENT:")
        logger.info(text_content)
        logger.info("-" * 50)
        logger.info("HTML CONTENT:")
        logger.info(html_content[:500] + "..." if len(html_content) > 500 else html_content)
        logger.info("=" * 50)
        
        # Log to database
        for recipient in recipients:
            EmailLog.objects.create(
                recipient_email=recipient,
                subject=subject,
                success=True,
                error_message="Development mode - not actually sent"
            )
        
        return True
    
    def send_daily_report(self, recipients: List[str], subject: str, html_content: str, text_content: str) -> bool:
        return self.send_email(recipients, subject, html_content, text_content, "daily_report")
    
    def send_to_group(self, group_name: str, subject: str, html_content: str, text_content: str, template_name: Optional[str] = None) -> bool:
        logger.info(f"Would send to group: {group_name}")
        return self.send_email([f"group-{group_name}@example.com"], subject, html_content, text_content, template_name)
    
    def test_connection(self) -> bool:
        return True


def get_email_service():
    """Factory function to get the appropriate email service"""
    if getattr(settings, 'DEBUG', False) or not getattr(settings, 'MAILGUN_API_KEY', None):
        return DevelopmentEmailService()
    else:
        return MailgunEmailService()
