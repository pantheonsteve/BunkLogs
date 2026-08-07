from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class BunksConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "bunk_logs.bunks"
    verbose_name = _("Legacy — Bunks (read-only)")
