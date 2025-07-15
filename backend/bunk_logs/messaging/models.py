from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from bunk_logs.utils.models import TestDataMixin, TimestampedTestDataMixin


class EmailTemplate(TimestampedTestDataMixin):
    """Model for storing email templates"""
    name = models.CharField(max_length=100, unique=True)
    subject_template = models.CharField(max_length=200)
    html_template = models.TextField()
    text_template = models.TextField()
    description = models.TextField(blank=True, help_text="Description of what this template is used for")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Email Template")
        verbose_name_plural = _("Email Templates")
        app_label = "messaging"
        db_table = 'bunk_logs_messaging_emailtemplate'

    def __str__(self):
        return self.name


class EmailRecipientGroup(TimestampedTestDataMixin):
    """Model for grouping email recipients"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Email Recipient Group")
        verbose_name_plural = _("Email Recipient Groups")
        app_label = "messaging"
        db_table = 'bunk_logs_messaging_emailrecipientgroup'

    def __str__(self):
        return self.name


class EmailRecipient(TimestampedTestDataMixin):
    """Model for storing email recipients"""
    email = models.EmailField()
    name = models.CharField(max_length=100, blank=True)
    group = models.ForeignKey(
        EmailRecipientGroup,
        on_delete=models.CASCADE,
        related_name="recipients"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Email Recipient")
        verbose_name_plural = _("Email Recipients")
        unique_together = ('email', 'group')
        app_label = "messaging"
        db_table = 'bunk_logs_messaging_emailrecipient'

    def __str__(self):
        return f"{self.name} <{self.email}>" if self.name else self.email


class EmailSchedule(TimestampedTestDataMixin):
    """Model for scheduling automated emails"""
    name = models.CharField(max_length=100, unique=True)
    template = models.ForeignKey(
        EmailTemplate,
        on_delete=models.CASCADE,
        related_name="schedules"
    )
    recipient_group = models.ForeignKey(
        EmailRecipientGroup,
        on_delete=models.CASCADE,
        related_name="schedules"
    )
    cron_expression = models.CharField(
        max_length=100,
        help_text="Cron expression for scheduling (e.g., '0 8 * * *' for daily at 8 AM)"
    )
    is_active = models.BooleanField(default=True)
    last_sent = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("Email Schedule")
        verbose_name_plural = _("Email Schedules")
        app_label = "messaging"
        db_table = 'bunk_logs_messaging_emailschedule'

    def __str__(self):
        return self.name


class EmailLog(TimestampedTestDataMixin):
    """Model for logging sent emails"""
    template = models.ForeignKey(
        EmailTemplate,
        on_delete=models.CASCADE,
        related_name="logs",
        null=True,
        blank=True
    )
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=200)
    sent_at = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    mailgun_message_id = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = _("Email Log")
        verbose_name_plural = _("Email Logs")
        ordering = ["-sent_at"]
        app_label = "messaging"
        db_table = 'bunk_logs_messaging_emaillog'

    def __str__(self):
        status = "✓" if self.success else "✗"
        return f"{status} {self.subject} to {self.recipient_email}"
