from django.urls import include
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import EmailLogViewSet
from .views import EmailPreviewViewSet
from .views import EmailRecipientGroupViewSet
from .views import EmailRecipientViewSet
from .views import EmailScheduleViewSet
from .views import EmailTemplateViewSet

router = DefaultRouter()
router.register(r"templates", EmailTemplateViewSet)
router.register(r"recipient-groups", EmailRecipientGroupViewSet)
router.register(r"recipients", EmailRecipientViewSet)
router.register(r"schedules", EmailScheduleViewSet)
router.register(r"logs", EmailLogViewSet)
router.register(r"preview", EmailPreviewViewSet, basename="email-preview")

urlpatterns = [
    path("", include(router.urls)),
]
