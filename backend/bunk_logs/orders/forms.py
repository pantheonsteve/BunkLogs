from django import forms
from .models import Order, OrderItem, Item, ItemCategory
from bunks.models import Bunk
from bunk_logs.users.models import User  # Use the fully qualified import path
from django.utils.translation import gettext_lazy as _

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            "user",
            "order_number",
            "order_status",
            "order_bunk",
        ]  # Only include fields that exist in the Order model

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = User.objects.all()
        self.fields["order_bunk"].queryset = Bunk.objects.all()


class OrderItemForm(forms.ModelForm):
    """Form for order items with a dropdown to select from available items."""
    item = forms.ModelChoiceField(
        queryset=Item.objects.filter(available=True),
        required=False,
        label=_("Select Item"),
        help_text=_("Select an item from the catalog")
    )
    
    class Meta:
        model = OrderItem
        fields = ['item', 'item_name', 'item_quantity']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['item_name'].widget = forms.TextInput(attrs={'class': 'item-name-field'})
        self.fields['item_name'].label = _("Item Name")
        self.fields['item_name'].help_text = _("You can either select an item from the dropdown or enter a custom item name")
        
        # Make item_name required
        self.fields['item_name'].required = True
    
    def clean(self):
        cleaned_data = super().clean()
        item = cleaned_data.get('item')
        
        # If an item is selected from the dropdown, use its name
        if item:
            cleaned_data['item_name'] = item.item_name
            
        return cleaned_data


class ItemCategoryCSVImportForm(forms.Form):
    """Form for importing ItemCategories from CSV."""
    csv_file = forms.FileField(
        label="CSV File",
        help_text="Please upload a CSV file with category_name and category_description columns."
    )
    dry_run = forms.BooleanField(
        required=False,
        label="Dry run",
        help_text="Validate the import without saving to database.",
        initial=True,
    )

    def clean(self):
        cleaned_data = super().clean()
        csv_file = cleaned_data.get("csv_file")
        if csv_file and not csv_file.name.endswith('.csv'):
            self.add_error("csv_file", "File must be a CSV file")
        return cleaned_data


class ItemCSVImportForm(forms.Form):
    """Form for importing Items from CSV."""
    csv_file = forms.FileField(
        label="CSV File",
        help_text="Please upload a CSV file with item_name, item_description, available, and category_name columns."
    )
    dry_run = forms.BooleanField(
        required=False,
        label="Dry run",
        help_text="Validate the import without saving to database.",
        initial=True,
    )
    
    def clean(self):
        cleaned_data = super().clean()
        csv_file = cleaned_data.get("csv_file")
        if csv_file and not csv_file.name.endswith('.csv'):
            self.add_error("csv_file", "File must be a CSV file")
        return cleaned_data