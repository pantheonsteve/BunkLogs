from django.apps import AppConfig


class BunklogsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "bunk_logs.bunklogs"

    def ready(self):
        # Wire up the StaffLog → core.Reflection dual-write signal
        # (Step 7_6g). The receiver is registered via @receiver decorator
        # so the import side-effect is what attaches the handler.
        from bunk_logs.bunklogs import signals  # noqa: F401
