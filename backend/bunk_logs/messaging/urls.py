from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    EmailTemplateViewSet,
    EmailRecipientGroupViewSet, 
    EmailRecipientViewSet,
    EmailScheduleViewSet,
    EmailLogViewSet,
    EmailPreviewViewSet
)

router = DefaultRouter()
router.register(r'templates', EmailTemplateViewSet)
router.register(r'recipient-groups', EmailRecipientGroupViewSet)
router.register(r'recipients', EmailRecipientViewSet)
router.register(r'schedules', EmailScheduleViewSet)
router.register(r'logs', EmailLogViewSet)
router.register(r'preview', EmailPreviewViewSet, basename='email-preview')

urlpatterns = [
    path('', include(router.urls)),
]
