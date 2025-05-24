import csv
from pathlib import Path
from typing import Any, Dict, List

from django.db import transaction

from ..models import ItemCategory, Item


class ItemCategoryImportError(ValueError):
    """Custom exception for item category import errors."""
    pass


class ItemImportError(ValueError):
    """Custom exception for item import errors."""
    pass


def _validate_category_name(name: str) -> None:
    """Validate that the category name is not empty."""
    if not name.strip():
        raise ItemCategoryImportError("Category name cannot be empty")


def _validate_item_fields(item_name: str, category_name: str) -> None:
    """Validate item fields."""
    if not item_name.strip():
        raise ItemImportError("Item name cannot be empty")
    if not category_name.strip():
        raise ItemImportError("Category name cannot be empty")


def import_item_categories_from_csv(file_path, *, dry_run=False) -> Dict[str, Any]:
    """Import item categories from CSV file.
    
    CSV should have columns: category_name, category_description
    """
    success_count = 0
    error_records = []
    file_path = Path(file_path)
    
    with file_path.open() as csv_file:
        reader = csv.DictReader(csv_file)
        
        for row_num, row in enumerate(reader, start=1):
            try:
                # Validate required fields
                if 'category_name' not in row:
                    raise ItemCategoryImportError("Missing 'category_name' column")
                
                # Data validation
                _validate_category_name(row.get('category_name', ''))
                
                # Prepare data
                category_data = {
                    'category_name': row['category_name'],
                    'category_description': row.get('category_description', ''),
                }
                
                # In dry run mode, we validate but don't save
                if not dry_run:
                    # Create or update category
                    category, created = ItemCategory.objects.update_or_create(
                        category_name=row['category_name'],
                        defaults=category_data,
                    )
                
                success_count += 1
            except (ValueError, TypeError, KeyError) as e:
                error_records.append({
                    'row': row_num,
                    'error': str(e),
                })
    
    return {
        'success_count': success_count,
        'error_count': len(error_records),
        'errors': error_records,
    }


def import_items_from_csv(file_path, *, dry_run=False) -> Dict[str, Any]:
    """Import items from CSV file.
    
    CSV should have columns: item_name, item_description, available, category_name
    """
    success_count = 0
    error_records = []
    file_path = Path(file_path)
    
    with file_path.open() as csv_file:
        reader = csv.DictReader(csv_file)
        
        for row_num, row in enumerate(reader, start=1):
            try:
                # Validate required fields
                if 'item_name' not in row:
                    raise ItemImportError("Missing 'item_name' column")
                if 'category_name' not in row:
                    raise ItemImportError("Missing 'category_name' column")
                
                # Data validation
                _validate_item_fields(row.get('item_name', ''), row.get('category_name', ''))
                
                # Look up the category
                category_name = row['category_name']
                try:
                    category = ItemCategory.objects.get(category_name=category_name)
                except ItemCategory.DoesNotExist:
                    if dry_run:
                        # In dry run mode, we just validate existence
                        raise ItemImportError(f"Category '{category_name}' does not exist")
                    else:
                        # Create the category if it doesn't exist
                        category = ItemCategory.objects.create(
                            category_name=category_name,
                            category_description=f"Auto-created category for {category_name}"
                        )
                
                # Parse available as boolean
                available = row.get('available', '').lower()
                if available in ('true', 'yes', '1', 'y'):
                    available = True
                elif available in ('false', 'no', '0', 'n', ''):
                    available = False
                else:
                    available = True  # Default to available
                
                # Prepare item data
                item_data = {
                    'item_name': row['item_name'],
                    'item_description': row.get('item_description', ''),
                    'available': available,
                    'item_category': category,
                }
                
                # In dry run mode, we validate but don't save
                if not dry_run:
                    # Create or update item
                    item, created = Item.objects.update_or_create(
                        item_name=row['item_name'],
                        defaults=item_data,
                    )
                
                success_count += 1
            except (ValueError, TypeError, KeyError) as e:
                error_records.append({
                    'row': row_num,
                    'error': str(e),
                })
    
    return {
        'success_count': success_count,
        'error_count': len(error_records),
        'errors': error_records,
    }
