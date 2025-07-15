from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponse

from .models import EmailTemplate, EmailRecipientGroup, EmailRecipient, EmailSchedule, EmailLog


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject_template', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'subject_template', 'description')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('name', 'subject_template', 'description', 'is_active')
        }),
        ('Templates', {
            'fields': ('html_template', 'text_template'),
            'classes': ('wide',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class EmailRecipientInline(admin.TabularInline):
    model = EmailRecipient
    extra = 1


@admin.register(EmailRecipientGroup)
class EmailRecipientGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'recipient_count', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [EmailRecipientInline]

    def recipient_count(self, obj):
        return obj.recipients.filter(is_active=True).count()
    recipient_count.short_description = 'Active Recipients'


@admin.register(EmailRecipient)
class EmailRecipientAdmin(admin.ModelAdmin):
    list_display = ('email', 'name', 'group', 'is_active', 'created_at')
    list_filter = ('group', 'is_active', 'created_at')
    search_fields = ('email', 'name', 'group__name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(EmailSchedule)
class EmailScheduleAdmin(admin.ModelAdmin):
    list_display = ('name', 'template', 'recipient_group', 'cron_expression', 'is_active', 'last_sent')
    list_filter = ('is_active', 'last_sent', 'created_at')
    search_fields = ('name', 'template__name', 'recipient_group__name')
    readonly_fields = ('created_at', 'updated_at', 'last_sent')
    
    fieldsets = (
        (None, {
            'fields': ('name', 'template', 'recipient_group', 'is_active')
        }),
        ('Scheduling', {
            'fields': ('cron_expression', 'last_sent'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ('subject', 'recipient_email', 'template', 'success', 'sent_at')
    list_filter = ('success', 'sent_at', 'template')
    search_fields = ('subject', 'recipient_email', 'template__name')
    readonly_fields = ('sent_at', 'created_at', 'updated_at')
    
    def has_add_permission(self, request):
        return False  # Email logs should only be created programmatically
    
    def has_change_permission(self, request, obj=None):
        return False  # Email logs should be read-only
    
    def success_display(self, obj):
        if obj.success:
            return format_html('<span style="color: green;">✓ Success</span>')
        else:
            return format_html('<span style="color: red;">✗ Failed</span>')
    success_display.short_description = 'Status'
