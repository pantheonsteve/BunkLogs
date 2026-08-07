from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CampersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "bunk_logs.campers"
    verbose_name = _("Legacy — Campers (read-only)")
