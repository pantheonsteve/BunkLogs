import tempfile
from pathlib import Path

from django.contrib import admin
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _

from .forms import ItemCategoryCSVImportForm, ItemCSVImportForm, OrderItemForm
from .models import Order, OrderItem, Item, ItemCategory
from .services.imports import import_item_categories_from_csv, import_items_from_csv


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    form = OrderItemForm
    extra = 1  # Number of empty forms to display
    fields = ('item', 'item_name', 'item_quantity')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "order_date",
        "order_number",
        "order_status",
        "order_bunk",
    )
    search_fields = ("user__username", "order_number")
    list_filter = ("order_status", "order_bunk")
    date_hierarchy = "order_date"
    ordering = ("-order_date",)
    autocomplete_fields = ["user", "order_bunk"]
    inlines = [OrderItemInline]  # Add the inline to display OrderItems

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        "item_name",
        "item_quantity",
        "order",
    )
    search_fields = ("item_name",)
    list_filter = ("order", "item__item_category")
    ordering = ("-order",)
    autocomplete_fields = ["order"]

    def item_category(self, obj):
        return obj.item.item_category if obj.item else None
    item_category.admin_order_field = 'item__item_category'
    item_category.short_description = 'Item Category'

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = (
        "item_name",
        "item_description",
        "available",
        "item_category",
    )
    search_fields = ("item_name",)
    list_filter = ("item_category", "available")
    ordering = ("item_name",)
    autocomplete_fields = ["item_category"]
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("import-items/", self.import_items, name="orders_item_import_csv"),
        ]
        return custom_urls + urls
    
    def import_items(self, request):
        if request.method == "POST":
            form = ItemCSVImportForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = form.cleaned_data["csv_file"]
                dry_run = form.cleaned_data["dry_run"]

                # Save the uploaded file to a secure temporary file
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    temp_path = Path(temp_file.name)
                    for chunk in csv_file.chunks():
                        temp_file.write(chunk)

                # Process the CSV file
                result = import_items_from_csv(temp_path, dry_run=dry_run)

                if dry_run:
                    messages.info(
                        request,
                        "Dry run completed. "
                        f"{result['success_count']} items would be imported.",
                    )
                else:
                    messages.success(
                        request,
                        f"Successfully imported {result['success_count']} items.",
                    )

                if result["error_count"] > 0:
                    for error in result["errors"]:
                        messages.error(
                            request,
                            f"Error in row {error['row']}: {error['error']}",
                        )

                # Clean up the temporary file
                temp_path.unlink(missing_ok=True)

                return redirect("admin:orders_item_changelist")
        else:
            form = ItemCSVImportForm()

        context = {
            "form": form,
            "title": "Import Items from CSV",
            "opts": self.model._meta,
            "app_label": self.model._meta.app_label,
            "model_name": self.model._meta.model_name,
        }
        return render(request, "admin/csv_form.html", context)
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["import_items"] = reverse("admin:orders_item_import_csv")
        return super().changelist_view(request, extra_context=extra_context)

@admin.register(ItemCategory)
class ItemCategoryAdmin(admin.ModelAdmin):
    list_display = (
        "category_name",
        "category_description",
    )
    search_fields = ("category_name",)
    list_filter = ("category_name",)
    ordering = ("category_name",)
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("import-categories/", self.import_categories, name="orders_itemcategory_import_csv"),
        ]
        return custom_urls + urls
    
    def import_categories(self, request):
        if request.method == "POST":
            form = ItemCategoryCSVImportForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = form.cleaned_data["csv_file"]
                dry_run = form.cleaned_data["dry_run"]

                # Save the uploaded file to a secure temporary file
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    temp_path = Path(temp_file.name)
                    for chunk in csv_file.chunks():
                        temp_file.write(chunk)

                # Process the CSV file
                result = import_item_categories_from_csv(temp_path, dry_run=dry_run)

                if dry_run:
                    messages.info(
                        request,
                        "Dry run completed. "
                        f"{result['success_count']} categories would be imported.",
                    )
                else:
                    messages.success(
                        request,
                        f"Successfully imported {result['success_count']} categories.",
                    )

                if result["error_count"] > 0:
                    for error in result["errors"]:
                        messages.error(
                            request,
                            f"Error in row {error['row']}: {error['error']}",
                        )

                # Clean up the temporary file
                temp_path.unlink(missing_ok=True)

                return redirect("admin:orders_itemcategory_changelist")
        else:
            form = ItemCategoryCSVImportForm()

        context = {
            "form": form,
            "title": "Import Item Categories from CSV",
            "opts": self.model._meta,
            "app_label": self.model._meta.app_label,
            "model_name": self.model._meta.model_name,
        }
        return render(request, "admin/csv_form.html", context)
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["import_categories"] = reverse("admin:orders_itemcategory_import_csv")
        return super().changelist_view(request, extra_context=extra_context)