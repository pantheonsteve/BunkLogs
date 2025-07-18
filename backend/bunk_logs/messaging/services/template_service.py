from django.template.loader import render_to_string
from django.conf import settings
from typing import Dict, Any

from ..models import EmailTemplate


class EmailTemplateService:
    """Service for rendering email templates"""
    
    def render_template(self, template_name: str, context: Dict[str, Any]) -> Dict[str, str]:
        """Render a template by name from the database"""
        try:
            template = EmailTemplate.objects.get(name=template_name, is_active=True)
            
            # Render subject
            subject = self._render_string_template(template.subject_template, context)
            
            # Render HTML content
            html_content = self._render_string_template(template.html_template, context)
            
            # Render text content
            text_content = self._render_string_template(template.text_template, context)
            
            return {
                'subject': subject,
                'html_content': html_content,
                'text_content': text_content
            }
            
        except EmailTemplate.DoesNotExist:
            raise ValueError(f"Email template '{template_name}' not found or inactive")
    
    def render_daily_orders_email(self, report_data: Dict[str, Any]) -> Dict[str, str]:
        """Render the daily orders email using file-based templates"""
        
        # Add additional context for the template
        context = {
            **report_data,
            'site_name': getattr(settings, 'SITE_NAME', 'CLC BunkLogs'),
            'site_url': getattr(settings, 'SITE_URL', 'https://clc.bunklogs.net'),
        }
        
        # Render templates
        html_content = render_to_string('email/daily_orders.html', context)
        text_content = render_to_string('email/text/daily_orders.txt', context)
        
        # Create subject
        subject = f"Daily Orders Report - {report_data['date'].strftime('%B %d, %Y')}"
        if report_data['total_orders'] == 0:
            subject += " (No Orders)"
        else:
            subject += f" ({report_data['total_orders']} Orders)"
        
        return {
            'subject': subject,
            'html_content': html_content,
            'text_content': text_content
        }
    
    def render_weekly_summary_email(self, report_data: Dict[str, Any]) -> Dict[str, str]:
        """Render the weekly summary email"""
        
        context = {
            **report_data,
            'site_name': getattr(settings, 'SITE_NAME', 'BunkLogs'),
            'site_url': getattr(settings, 'SITE_URL', 'https://bunklogs.com'),
        }
        
        # Render templates
        html_content = render_to_string('email/weekly_summary.html', context)
        text_content = render_to_string('email/text/weekly_summary.txt', context)
        
        # Create subject
        start_date = report_data['start_date'].strftime('%m/%d')
        end_date = report_data['end_date'].strftime('%m/%d/%Y')
        subject = f"Weekly Orders Summary - {start_date} - {end_date}"
        
        return {
            'subject': subject,
            'html_content': html_content,
            'text_content': text_content
        }
    
    def _render_string_template(self, template_string: str, context: Dict[str, Any]) -> str:
        """Render a template string with Django template syntax"""
        from django.template import Template, Context
        
        template = Template(template_string)
        django_context = Context(context)
        return template.render(django_context)
