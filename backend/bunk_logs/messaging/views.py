from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from django.utils import timezone
from datetime import date, timedelta

from .models import EmailTemplate, EmailRecipientGroup, EmailRecipient, EmailSchedule, EmailLog
from .serializers import (
    EmailTemplateSerializer, 
    EmailRecipientGroupSerializer, 
    EmailRecipientSerializer,
    EmailScheduleSerializer,
    EmailLogSerializer
)
from .services.report_service import DailyReportService
from .services.template_service import EmailTemplateService
from .services.email_service import get_email_service


class EmailTemplateViewSet(viewsets.ModelViewSet):
    queryset = EmailTemplate.objects.all()
    serializer_class = EmailTemplateSerializer
    permission_classes = [IsAuthenticated]


class EmailRecipientGroupViewSet(viewsets.ModelViewSet):
    queryset = EmailRecipientGroup.objects.all()
    serializer_class = EmailRecipientGroupSerializer
    permission_classes = [IsAuthenticated]


class EmailRecipientViewSet(viewsets.ModelViewSet):
    queryset = EmailRecipient.objects.all()
    serializer_class = EmailRecipientSerializer
    permission_classes = [IsAuthenticated]


class EmailScheduleViewSet(viewsets.ModelViewSet):
    queryset = EmailSchedule.objects.all()
    serializer_class = EmailScheduleSerializer
    permission_classes = [IsAuthenticated]


class EmailLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = EmailLog.objects.all()
    serializer_class = EmailLogSerializer
    permission_classes = [IsAuthenticated]


class EmailPreviewViewSet(viewsets.ViewSet):
    """ViewSet for previewing emails"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def daily_report(self, request):
        """Preview daily report email"""
        date_param = request.GET.get('date')
        format_param = request.GET.get('format', 'html')  # html, json, or text
        
        if date_param:
            try:
                target_date = date.fromisoformat(date_param)
            except ValueError:
                return Response({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            target_date = timezone.now().date()
        
        try:
            # Generate report data
            report_service = DailyReportService()
            report_data = report_service.generate_daily_report_data(target_date)
            
            # Render email template
            template_service = EmailTemplateService()
            email_content = template_service.render_daily_orders_email(report_data)
            
            if format_param == 'html':
                return HttpResponse(email_content['html_content'], content_type='text/html')
            elif format_param == 'text':
                return HttpResponse(email_content['text_content'], content_type='text/plain')
            else:  # json
                return Response({
                    'subject': email_content['subject'],
                    'html_content': email_content['html_content'],
                    'text_content': email_content['text_content'],
                    'report_data': {
                        'date': str(target_date),
                        'total_orders': report_data['total_orders'],
                        'maintenance_count': report_data['maintenance_count'],
                        'camper_care_count': report_data['camper_care_count'],
                        'bunks_with_orders_count': report_data['bunks_with_orders_count'],
                        'has_orders': report_data['has_orders'],
                    }
                })
                
        except Exception as e:
            return Response(
                {'error': f'Error generating preview: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def send_test(self, request):
        """Send a test email"""
        recipients = request.data.get('recipients', [])
        if not recipients:
            return Response({'error': 'Recipients required'}, status=status.HTTP_400_BAD_REQUEST)
        
        date_param = request.data.get('date')
        if date_param:
            try:
                target_date = date.fromisoformat(date_param)
            except ValueError:
                return Response({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            target_date = timezone.now().date()
        
        try:
            # Generate report data
            report_service = DailyReportService()
            report_data = report_service.generate_daily_report_data(target_date)
            
            # Render email template
            template_service = EmailTemplateService()
            email_content = template_service.render_daily_orders_email(report_data)
            
            # Send email
            email_service = get_email_service()
            success = email_service.send_email(
                recipients=recipients,
                **email_content
            )
            
            if success:
                return Response({'message': f'Test email sent successfully to {len(recipients)} recipients'})
            else:
                return Response({'error': 'Failed to send test email'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            return Response(
                {'error': f'Error sending test email: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
