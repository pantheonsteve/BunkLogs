from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from bunk_logs.utils.metrics import user_logged_in as metric_user_logged_in


@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    metric_user_logged_in()
