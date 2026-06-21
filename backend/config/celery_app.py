import os

try:
    from ddtrace import patch_all

    patch_all()
except ImportError:
    pass

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("bunk_logs")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
