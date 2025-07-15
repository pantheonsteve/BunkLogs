from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class MessagingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "bunk_logs.messaging"
    verbose_name = _("Messaging")

    def ready(self):
        # Import any signals here when they're created
        pass
