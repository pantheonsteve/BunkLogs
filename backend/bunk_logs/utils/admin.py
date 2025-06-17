"""
Admin interface for test data management.
"""
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib import messages
from django.utils.html import format_html


class TestDataFilter(SimpleListFilter):
    """Filter for separating test data from production data."""
    title = 'Data Type'
    parameter_name = 'is_test_data'

    def lookups(self, request, model_admin):
        return (
            ('1', 'Test Data'),
            ('0', 'Production Data'),
        )

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.filter(is_test_data=True)
        if self.value() == '0':
            return queryset.filter(is_test_data=False)
        return queryset


class TestDataAdminMixin:
    """
    Mixin for Django admin to help manage test data.
    Add this to your ModelAdmin classes that inherit from TestDataMixin.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add test data filter to existing list filters
        current_filters = list(getattr(self, 'list_filter', ()))
        if TestDataFilter not in current_filters:
            current_filters.append(TestDataFilter)
        self.list_filter = tuple(current_filters)
        
        # Add is_test_data to list display if not already present
        current_display = list(getattr(self, 'list_display', ()))
        if 'is_test_data_colored' not in current_display and 'is_test_data' not in current_display:
            current_display.append('is_test_data_colored')
        self.list_display = tuple(current_display)
    
    def get_actions(self, request):
        """Add custom actions for test data management."""
        actions = super().get_actions(request)
        # Manually add the actions from the mixin - use the class methods, not self methods
        actions['mark_as_test_data'] = (TestDataAdminMixin.mark_as_test_data, 'mark_as_test_data', TestDataAdminMixin.mark_as_test_data.short_description)
        actions['mark_as_production_data'] = (TestDataAdminMixin.mark_as_production_data, 'mark_as_production_data', TestDataAdminMixin.mark_as_production_data.short_description)
        actions['delete_test_data'] = (TestDataAdminMixin.delete_test_data, 'delete_test_data', TestDataAdminMixin.delete_test_data.short_description)
        return actions
    
    def mark_as_test_data(self, request, queryset):
        """Mark selected items as test data."""
        updated = queryset.update(is_test_data=True)
        self.message_user(
            request,
            f'{updated} item(s) marked as test data.',
            messages.SUCCESS
        )
    mark_as_test_data.short_description = "Mark selected items as test data"
    
    def mark_as_production_data(self, request, queryset):
        """Mark selected items as production data."""
        updated = queryset.update(is_test_data=False)
        self.message_user(
            request,
            f'{updated} item(s) marked as production data.',
            messages.SUCCESS
        )
    mark_as_production_data.short_description = "Mark selected items as production data"
    
    def delete_test_data(self, request, queryset):
        """Delete only test data from selected items."""
        test_data = queryset.filter(is_test_data=True)
        count = test_data.count()
        if count > 0:
            test_data.delete()
            self.message_user(
                request,
                f'{count} test data item(s) deleted.',
                messages.SUCCESS
            )
        else:
            self.message_user(
                request,
                'No test data found in selection.',
                messages.WARNING
            )
    delete_test_data.short_description = "Delete test data from selection"
    
    def is_test_data_colored(self, obj):
        """Display is_test_data with color coding."""
        if obj.is_test_data:
            return format_html('<span style="color: red; font-weight: bold;">Test Data</span>')
        else:
            return format_html('<span style="color: green;">Production</span>')
    is_test_data_colored.short_description = 'Data Type'
    is_test_data_colored.admin_order_field = 'is_test_data'
