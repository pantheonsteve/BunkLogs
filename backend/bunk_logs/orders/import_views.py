
from django.shortcuts import redirect
from django.contrib import messages
from django.template.response import TemplateResponse
import csv
import io
from .models import Order, Item, ItemCategory, OrderItem
from .forms import ItemCategoryImportForm, ItemImportForm, OrderImportForm

def import_orders(request):
    """
    Handle importing orders
    """
    if request.method == 'POST':
        form = OrderImportForm(request.POST, request.FILES)
        if form.is_valid():
            # Process the CSV file
            csv_file = form.cleaned_data['csv_file']
            csv_data = csv_file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(csv_data))
            
            order_type = form.cleaned_data['order_type']
            
            # Track import statistics
            created_count = 0
            updated_count = 0
            error_count = 0
            error_messages = []
            
            # Process each row and create orders
            for row in csv_reader:
                try:
                    # Required fields
                    user_id = row.get('user_id', '').strip()
                    order_bunk_id = row.get('order_bunk_id', '').strip()
                    
                    if not user_id or not order_bunk_id:
                        error_count += 1
                        error_messages.append(f"Row {csv_reader.line_num}: Missing required field (user_id or order_bunk_id)")
                        continue
                    
                    # Create the order
                    order_status = row.get('order_status', 'submitted').strip()
                    if order_status not in ['submitted', 'pending', 'completed', 'cancelled']:
                        order_status = 'submitted'  # Default if invalid status
                    
                    # Create the order with specified fields
                    order = Order.objects.create(
                        user_id=user_id,
                        order_bunk_id=order_bunk_id,
                        order_type=order_type,
                        order_status=order_status
                    )
                    
                    # Process order items if included
                    items_str = row.get('items', '').strip()
                    if items_str:
                        # Format expected: "item_id:quantity,item_id:quantity"
                        try:
                            items_pairs = items_str.split(',')
                            for pair in items_pairs:
                                if ':' in pair:
                                    item_id, quantity = pair.split(':')
                                    OrderItem.objects.create(
                                        order=order,
                                        item_id=item_id.strip(),
                                        item_quantity=int(quantity.strip())
                                    )
                        except Exception as item_error:
                            error_messages.append(f"Order {order.id}, Row {csv_reader.line_num}: Error processing items - {str(item_error)}")
                    
                    created_count += 1
                    
                except Exception as e:
                    error_count += 1
                    error_messages.append(f"Row {csv_reader.line_num}: {str(e)}")
            
            # Show import results
            if created_count > 0:
                messages.success(request, f"Successfully created {created_count} orders.")
            if error_count > 0:
                messages.error(request, f"Encountered {error_count} errors during import.")
                for msg in error_messages[:10]:  # Show first 10 errors
                    messages.warning(request, msg)
                if len(error_messages) > 10:
                    messages.warning(request, f"...and {len(error_messages) - 10} more errors.")
            
            return redirect('admin:orders_order_changelist')
    else:
        form = OrderImportForm()
    
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
        form = ItemImportForm(request.POST, request.FILES)
        if form.is_valid():
            # Process the CSV file
            csv_file = form.cleaned_data['csv_file']
            csv_data = csv_file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(csv_data))

            # Track import statistics
            created_count = 0
            updated_count = 0
            error_count = 0
            error_messages = []

            # Process each row and create or update items
            for row in csv_reader:
                try:
                    # Check if this item already exists
                    item_name = row.get('item_name', '').strip()
                    if not item_name:
                        error_count += 1
                        error_messages.append(f"Row {csv_reader.line_num}: Missing item name")
                        continue
                    
                    # Validate required fields
                    item_category_id = row.get('item_category_id', '').strip()
                    if not item_category_id:
                        error_count += 1
                        error_messages.append(f"Row {csv_reader.line_num}: Missing item category ID")
                        continue
                    
                    # Parse boolean field
                    available_str = row.get('available', 'True').strip().lower()
                    available = available_str in ('true', '1', 'yes', 'y')
                    
                    # Get or create the item
                    item, created = Item.objects.update_or_create(
                        item_name=item_name,
                        defaults={
                            'item_description': row.get('item_description', ''),
                            'available': available,
                            'item_category_id': item_category_id
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
                messages.success(request, f"Successfully created {created_count} items.")
            if updated_count > 0:
                messages.info(request, f"Updated {updated_count} existing items.")
            if error_count > 0:
                messages.error(request, f"Encountered {error_count} errors during import.")
                for msg in error_messages[:10]:  # Show first 10 errors
                    messages.warning(request, msg)
                if len(error_messages) > 10:
                    messages.warning(request, f"...and {len(error_messages) - 10} more errors.")
                    
            return redirect('admin:orders_item_changelist')
    else:
        form = ItemImportForm()
    
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
            csv_file = form.cleaned_data['csv_file']
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
