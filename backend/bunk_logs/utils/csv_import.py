"""
Utility functions for importing CSV data with test data tracking.
"""
import csv
from typing import Dict, List, Any, Optional
from django.core.exceptions import ValidationError


def import_csv_with_test_flag(
    csv_file_path: str,
    model_class,
    field_mapping: Dict[str, str],
    is_test_data: bool = False,
    unique_fields: Optional[List[str]] = None,
    update_existing: bool = False
) -> Dict[str, int]:
    """
    Import CSV data into a Django model with test data tracking.
    
    Args:
        csv_file_path: Path to the CSV file
        model_class: Django model class to import data into
        field_mapping: Dictionary mapping CSV column names to model field names
        is_test_data: Whether to mark imported records as test data
        unique_fields: List of fields to use for checking existing records
        update_existing: Whether to update existing records or skip them
        
    Returns:
        Dictionary with counts of created, updated, and skipped records
        
    Example:
        field_mapping = {
            'First Name': 'first_name',
            'Last Name': 'last_name', 
            'Email': 'email',
            'Birth Date': 'date_of_birth'
        }
        
        result = import_csv_with_test_flag(
            'campers_test_data.csv',
            Camper,
            field_mapping,
            is_test_data=True,
            unique_fields=['email']
        )
    """
    created_count = 0
    updated_count = 0
    skipped_count = 0
    errors = []
    
    unique_fields = unique_fields or []
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 because row 1 is headers
                try:
                    # Map CSV columns to model fields
                    data = {}
                    for csv_col, model_field in field_mapping.items():
                        if csv_col in row and row[csv_col].strip():
                            data[model_field] = row[csv_col].strip()
                    
                    # Add test data flag
                    data['is_test_data'] = is_test_data
                    
                    # Check if record exists based on unique fields
                    existing_record = None
                    if unique_fields:
                        lookup_data = {
                            field: data[field] 
                            for field in unique_fields 
                            if field in data
                        }
                        if lookup_data:
                            try:
                                existing_record = model_class.objects.get(**lookup_data)
                            except model_class.DoesNotExist:
                                pass
                            except model_class.MultipleObjectsReturned:
                                errors.append(f"Row {row_num}: Multiple records found for {lookup_data}")
                                skipped_count += 1
                                continue
                    
                    if existing_record:
                        if update_existing:
                            # Update existing record
                            for field, value in data.items():
                                setattr(existing_record, field, value)
                            existing_record.full_clean()
                            existing_record.save()
                            updated_count += 1
                        else:
                            skipped_count += 1
                    else:
                        # Create new record
                        new_record = model_class(**data)
                        new_record.full_clean()
                        new_record.save()
                        created_count += 1
                        
                except ValidationError as e:
                    errors.append(f"Row {row_num}: Validation error - {e}")
                    skipped_count += 1
                except Exception as e:
                    errors.append(f"Row {row_num}: Error - {e}")
                    skipped_count += 1
                    
    except FileNotFoundError:
        raise FileNotFoundError(f"CSV file not found: {csv_file_path}")
    except Exception as e:
        raise Exception(f"Error reading CSV file: {e}")
    
    result = {
        'created': created_count,
        'updated': updated_count,
        'skipped': skipped_count,
        'errors': errors,
        'total_processed': created_count + updated_count + skipped_count
    }
    
    return result


def mark_existing_data_as_test(model_class, filters: Dict[str, Any]) -> int:
    """
    Mark existing data as test data based on filters.
    
    Args:
        model_class: Django model class
        filters: Dictionary of field filters to identify records
        
    Returns:
        Number of records updated
        
    Example:
        # Mark all campers with 'test' in their name as test data
        count = mark_existing_data_as_test(
            Camper, 
            {'first_name__icontains': 'test'}
        )
    """
    queryset = model_class.objects.filter(**filters)
    count = queryset.update(is_test_data=True)
    return count
