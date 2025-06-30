from django.contrib import admin
from django.urls import path
from django.urls import reverse
from django.utils.html import format_html
from django import forms

from .models import Order, OrderItem, Item, OrderType, ItemCategory, BunkLogsOrderTypeItemCategory
from bunk_logs.utils.admin import TestDataAdminMixin

# Custom admin for import feature
class ImportAdminMixin:
    """Mixin for import functionality in admin"""
    change_list_template = 'admin/orders/change_list.html'
    
    def get_urls(self):
        """Add import URL to admin URLs"""
        urls = super().get_urls()
        model_name = self.model._meta.model_name
        custom_urls = [
            path('import/', self.admin_site.admin_view(self.import_view),
                name=f'orders_{model_name}_import'),
        ]
        return custom_urls + urls
    
    def changelist_view(self, request, extra_context=None):
        """Add the import button to the changelist view"""
        extra_context = extra_context or {}
        model_name = self.model._meta.model_name
        url_name = f'admin:orders_{model_name}_import'
        try:
            extra_context['import_url'] = reverse(url_name)
        except Exception:
            # If the URL can't be reversed, don't show the button
            pass
        return super().changelist_view(request, extra_context=extra_context)

# Custom OrderItem form for dynamic item filtering
class OrderItemForm(forms.ModelForm):
    """Custom form for OrderItem with filtered item dropdown"""
    class Meta:
        model = OrderItem
        fields = ['item', 'item_quantity']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only filter items if the parent order is available and the form is bound to an instance
        if self.instance and hasattr(self.instance, 'order') and self.instance.order:
            order = self.instance.order
            # Get available item categories for this order's type
            available_categories = order.order_type.item_categories.all()
            # Filter items to only show those from these categories
            self.fields['item'].queryset = Item.objects.filter(
                item_category__in=available_categories,
                available=True
            )
            # Set a helpful help text
            category_names = ", ".join([cat.category_name for cat in available_categories])
            self.fields['item'].help_text = f"Available items from categories: {category_names}"
        else:
            # If creating a new inline item with no parent order yet, 
            # show a placeholder message in the dropdown
            self.fields['item'].help_text = "Select an Order Type first, then items will be filtered automatically."
            # Empty queryset initially - our JavaScript will populate it
            self.fields['item'].choices = [('', '---------')]

# Inline classes first
class OrderItemInline(admin.TabularInline):
    """Inline admin for OrderItems in an Order"""
    model = OrderItem
    form = OrderItemForm
    extra = 1

class CategoryInline(admin.TabularInline):
    """Inline admin for the relationship between OrderType and ItemCategory"""
    model = BunkLogsOrderTypeItemCategory
    extra = 1
    verbose_name = "Item Category"
    verbose_name_plural = "Item Categories"

@admin.register(Order)
class OrderAdmin(TestDataAdminMixin, ImportAdminMixin, admin.ModelAdmin):
    list_display = ('id', 'user', 'order_date', 'order_bunk', 'order_status')
    search_fields = ('user__email', 'order_status')
    list_filter = ('order_status', 'order_date', 'order_type', 'order_bunk')
    ordering = ('-order_date',)
    readonly_fields = ('order_date', 'user_email')
    fieldsets = (
        (None, {
            'fields': ('user', 'order_date', 'order_status', 'order_bunk')
        }),
        ('Order Details', {
            'fields': ('order_type', 'additional_notes', 'narrative_description')
        }),
    )
    inlines = [OrderItemInline]
    # Use our custom change form template for better UX
    change_form_template = 'admin/orders/order_change_form.html'
    
    def user_email(self, obj):
        return obj.user.email if obj.user else 'N/A'
    user_email.short_description = 'User Email'
    user_email.admin_order_field = 'user__email'
    
    def get_urls(self):
        """Add AJAX URL to fetch data for dynamic item filtering"""
        urls = super().get_urls()
        custom_urls = [
            path('get_type_categories/', self.admin_site.admin_view(self.get_type_categories),
                name='orders_order_get_type_categories'),
        ]
        return custom_urls + urls
    
    def get_type_categories(self, request):
        """AJAX view to get category data for order types"""
        from django.http import JsonResponse
        
        # Get all order types with their categories
        order_type_categories = {}
        for order_type in OrderType.objects.all():
            order_type_categories[order_type.id] = list(
                order_type.item_categories.values_list('id', flat=True)
            )
        
        # Get all items with their categories
        item_categories = {}
        item_names = {}
        for item in Item.objects.filter(available=True):
            item_categories[item.id] = item.item_category_id
            item_names[item.id] = item.item_name
            
        return JsonResponse({
            'order_type_categories': order_type_categories,
            'item_categories': item_categories,
            'item_names': item_names,
        })
    
    def import_view(self, request):
        """View for importing orders"""
        from .import_views import import_orders
        return import_orders(request)

@admin.register(Item)
class ItemAdmin(TestDataAdminMixin, ImportAdminMixin, admin.ModelAdmin):
    list_display = ('id', 'item_name', 'available', 'item_category')
    search_fields = ('item_name', 'item_category__category_name')
    list_filter = ('available', 'item_category')
    ordering = ('item_name',)
    fieldsets = (
        (None, {
            'fields': ('item_name', 'item_description', 'available', 'item_category')
        }),
    )
    
    def import_view(self, request):
        """View for importing items"""
        from .import_views import import_items
        return import_items(request)

@admin.register(OrderType)
class OrderTypeAdmin(TestDataAdminMixin, admin.ModelAdmin):
    list_display = ('id', 'type_name', 'get_categories')
    search_fields = ('type_name',)
    ordering = ('type_name',)
    fieldsets = (
        (None, {
            'fields': ('type_name', 'type_description')
        }),
    )
    inlines = [CategoryInline]

    def get_categories(self, obj):
        """Return a list of categories for display in the admin"""
        return ", ".join([c.category_name for c in obj.item_categories.all()[:5]])
    get_categories.short_description = "Categories"

@admin.register(ItemCategory)
class ItemCategoryAdmin(TestDataAdminMixin, ImportAdminMixin, admin.ModelAdmin):
    list_display = ('id', 'category_name')
    search_fields = ('category_name',)
    ordering = ('category_name',)
    fieldsets = (
        (None, {
            'fields': ('category_name', 'category_description')
        }),
    )
    
    def import_view(self, request):
        """View for importing item categories"""
        from .import_views import import_item_categories
        return import_item_categories(request)
