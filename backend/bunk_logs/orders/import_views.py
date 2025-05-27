
from django.shortcuts import render, redirect
from django.contrib import messages
from django.template.response import TemplateResponse
from django import forms
from django.core.exceptions import ValidationError
import csv
import io
from .models import Order, Item, ItemCategory

class ImportForm(forms.Form):
    """Base form for imports"""
    file = forms.FileField(
        label='Import File',
        help_text='Upload a file to import data.'
    )
    
class ItemCategoryImportForm(ImportForm):
    """Form for importing item categories"""
    
    def clean_file(self):
        """Validate that the uploaded file is a CSV with the correct format"""
        file = self.cleaned_data['file']
        
        # Check file extension
        if not file.name.endswith('.csv'):
            raise ValidationError('File must be a CSV file with .csv extension.')
        
        # Try to read the CSV file to validate format
        try:
            csv_file = io.StringIO(file.read().decode('utf-8'))
            reader = csv.reader(csv_file)
            header = next(reader)  # Read header row
            
            # Check if the required columns are in the header
            required_fields = ['category_name', 'category_description']
            for field in required_fields:
                if field not in header:
                    raise ValidationError(f'CSV file must contain a {field} column')
                    
            # Reset the file pointer so it can be read again later
            file.seek(0)
            return file
        except Exception as e:
            raise ValidationError(f'Invalid CSV file: {str(e)}')

def import_orders(request):
    """
    Handle importing orders
    """
    if request.method == 'POST':
        form = ImportForm(request.POST, request.FILES)
        if form.is_valid():
            # Process the form data (not implemented yet)
            messages.info(request, "Order import feature is not yet implemented.")
            return redirect('admin:orders_order_changelist')
    else:
        form = ImportForm()
    
    # Display the import form
    context = {
        'opts': Order._meta,
        'title': 'Import Orders',
        'form': form,
    }
    return TemplateResponse(request, 'admin/orders/import_form.html', context)

def import_items(request):
    """
    Handle importing items
    """
    if request.method == 'POST':
        form = ImportForm(request.POST, request.FILES)
        if form.is_valid():
            # Process the form data (not implemented yet)
            messages.info(request, "Item import feature is not yet implemented.")
            return redirect('admin:orders_item_changelist')
    else:
        form = ImportForm()
    
    # Display the import form
    context = {
        'opts': Item._meta,
        'title': 'Import Items',
        'form': form,
    }
    return TemplateResponse(request, 'admin/orders/import_form.html', context)

def import_item_categories(request):
    """
    Handle importing item categories
    """
    if request.method == 'POST':
        form = ItemCategoryImportForm(request.POST, request.FILES)
        if form.is_valid():
            # Process the CSV file
            csv_file = form.cleaned_data['file']
            csv_data = csv_file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(csv_data))
            
            # Track import statistics
            created_count = 0
            updated_count = 0
            error_count = 0
            error_messages = []
            
            # Process each row and create or update item categories
            for row in csv_reader:
                try:
                    # Check if this category already exists
                    category_name = row.get('category_name', '').strip()
                    if not category_name:
                        error_count += 1
                        error_messages.append(f"Row {csv_reader.line_num}: Missing category name")
                        continue
                        
                    # Get or create the item category
                    category, created = ItemCategory.objects.update_or_create(
                        category_name=category_name,
                        defaults={
                            'category_description': row.get('category_description', '')
                        }
                    )
                    
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
                        
                except Exception as e:
                    error_count += 1
                    error_messages.append(f"Row {csv_reader.line_num}: {str(e)}")
            
            # Show import results
            if created_count > 0:
                messages.success(request, f"Successfully created {created_count} item categories.")
            if updated_count > 0:
                messages.info(request, f"Updated {updated_count} existing item categories.")
            if error_count > 0:
                messages.error(request, f"Encountered {error_count} errors during import.")
                for msg in error_messages[:10]:  # Show first 10 errors
                    messages.warning(request, msg)
                if len(error_messages) > 10:
                    messages.warning(request, f"...and {len(error_messages) - 10} more errors.")
            
            return redirect('admin:orders_itemcategory_changelist')
    else:
        form = ItemCategoryImportForm()
    
    # Display the import form
    context = {
        'opts': ItemCategory._meta,
        'title': 'Import Item Categories',
        'form': form,
    }
    return TemplateResponse(request, 'admin/orders/import_form.html', context)
