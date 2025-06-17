# Test Data Management System

## Overview

This system provides an easy way to identify and manage dummy/testing data in your BunkLogs application. All models now include an `is_test_data` field that allows you to mark records as test data, making it simple to clean them up later.

## Features

- **Automatic Test Data Tracking**: All models inherit from `TestDataMixin` which adds an `is_test_data` boolean field
- **Bulk Operations**: Easy methods to query, count, and delete test data
- **Admin Interface Integration**: Admin pages include filters, actions, and visual indicators for test data
- **CSV Import Support**: Utility functions to mark imported CSV data as test data
- **Management Commands**: Django commands to clean up test data across all models

## Models with Test Data Support

All the following models now support test data tracking:

- **Users**: `User`
- **Campers**: `Camper`, `CamperBunkAssignment`
- **Bunks**: `Cabin`, `Session`, `Unit`, `Bunk`
- **Logs**: `BunkLog`
- **Orders**: `Order`, `OrderItem`, `Item`, `ItemCategory`, `OrderType`, `BunkLogsOrderTypeItemCategory`

## How to Use

### 1. Importing CSV Data as Test Data

When importing CSV data, you can mark it as test data using the utility functions:

```python
from bunk_logs.utils.csv_import import import_csv_with_test_flag
from bunk_logs.campers.models import Camper

# Import campers from CSV and mark as test data
field_mapping = {
    'First Name': 'first_name',
    'Last Name': 'last_name', 
    'Email': 'email',
    'Birth Date': 'date_of_birth'
}

result = import_csv_with_test_flag(
    'test_campers.csv',           # Path to CSV file
    Camper,                       # Model class
    field_mapping,                # Column mapping
    is_test_data=True,           # Mark as test data
    unique_fields=['email']       # Fields to check for duplicates
)

print(f"Created: {result['created']}")
print(f"Updated: {result['updated']}")
print(f"Skipped: {result['skipped']}")
print(f"Errors: {len(result['errors'])}")
```

### 2. Marking Existing Data as Test Data

If you have existing data that should be marked as test data:

```python
from bunk_logs.utils.csv_import import mark_existing_data_as_test
from bunk_logs.campers.models import Camper

# Mark all campers with 'test' in their name as test data
count = mark_existing_data_as_test(
    Camper, 
    {'first_name__icontains': 'test'}
)
print(f"Marked {count} campers as test data")
```

### 3. Using Model Methods

Each model now has convenient methods for working with test data:

```python
from bunk_logs.campers.models import Camper

# Get all test data
test_campers = Camper.get_test_data_queryset()
print(f"Found {test_campers.count()} test campers")

# Get all production data
production_campers = Camper.get_production_data_queryset()
print(f"Found {production_campers.count()} production campers")

# Delete all test data for this model
deleted_count = Camper.delete_all_test_data()
print(f"Deleted {deleted_count} test campers")
```

### 4. Using Django Admin

The admin interface now includes:

- **Filter by Test Data**: Use the "Data Type" filter to see only test data or production data
- **Visual Indicators**: Test data is highlighted in red, production data in green
- **Bulk Actions**:
  - Mark selected items as test data
  - Mark selected items as production data
  - Delete test data from selection

### 5. Management Commands

#### Clean Up All Test Data

```bash
# Dry run - see what would be deleted
python manage.py cleanup_test_data

# Actually delete all test data
python manage.py cleanup_test_data --confirm

# Clean up test data from specific app
python manage.py cleanup_test_data --app campers --confirm

# Clean up test data from specific model
python manage.py cleanup_test_data --model Camper --confirm
```

## CSV Import Examples

### Example 1: Import Test Campers

Create a CSV file `test_campers.csv`:
```csv
First Name,Last Name,Email,Birth Date
Test Camper,One,test1@example.com,2010-01-01
Test Camper,Two,test2@example.com,2011-02-15
Test Camper,Three,test3@example.com,2012-03-20
```

Import it as test data:
```python
from bunk_logs.utils.csv_import import import_csv_with_test_flag
from bunk_logs.campers.models import Camper

field_mapping = {
    'First Name': 'first_name',
    'Last Name': 'last_name',
    'Email': 'email',
    'Birth Date': 'date_of_birth'
}

result = import_csv_with_test_flag(
    'test_campers.csv',
    Camper,
    field_mapping,
    is_test_data=True,
    unique_fields=['email']
)
```

### Example 2: Import Test Orders

Create a CSV file `test_orders.csv`:
```csv
User Email,Bunk Name,Order Type,Status
test@example.com,Cabin A - Session 1,Maintenance,submitted
test2@example.com,Cabin B - Session 1,Camper Care,pending
```

Import script:
```python
from bunk_logs.utils.csv_import import import_csv_with_test_flag
from bunk_logs.orders.models import Order
from bunk_logs.users.models import User
from bunk_logs.bunks.models import Bunk
from bunk_logs.orders.models import OrderType

# You would need a custom import function for complex relationships
# This is just an example of the concept
```

## Best Practices

### 1. Always Mark Test Data
When importing CSV files for testing purposes, always set `is_test_data=True`:

```python
result = import_csv_with_test_flag(
    csv_file,
    Model,
    field_mapping,
    is_test_data=True  # Always set this for test imports
)
```

### 2. Use Descriptive Test Data
Make test data easily identifiable:
- Use prefixes like "Test" in names
- Use test email domains like "@test.com"
- Use obvious fake data

### 3. Regular Cleanup
Regularly clean up test data, especially before production deployments:

```bash
# Before deploying to production
python manage.py cleanup_test_data --confirm
```

### 4. Separate Test and Production Imports
Keep test CSV files separate from production data and always verify the `is_test_data` flag before importing.

## API Usage

You can also work with test data through the API:

```python
# In Django shell or scripts
from django.contrib.auth import get_user_model
User = get_user_model()

# Create a test user
test_user = User.objects.create(
    email='test@example.com',
    first_name='Test',
    last_name='User',
    is_test_data=True  # Mark as test data
)

# Query test users
test_users = User.objects.filter(is_test_data=True)
production_users = User.objects.filter(is_test_data=False)
```

## Troubleshooting

### Issue: CSV Import Not Marking as Test Data
- Ensure you're using `import_csv_with_test_flag()` function
- Verify `is_test_data=True` is set
- Check that the model inherits from `TestDataMixin`

### Issue: Can't Delete Test Data
- Check for foreign key constraints
- Use the management command which handles deletion order
- Delete dependent objects first (e.g., BunkLogs before Campers)

### Issue: Test Data Not Showing in Admin
- Ensure the admin class inherits from `TestDataAdminMixin`
- Check that the model has the `is_test_data` field
- Verify the admin registration is correct

## Advanced Usage

### Custom Deletion Order
The management command deletes test data in a specific order to handle foreign key constraints:

1. BunkLog
2. OrderItem
3. Order
4. CamperBunkAssignment
5. Bunk
6. Camper
7. Item
8. OrderType
9. BunkLogsOrderTypeItemCategory
10. ItemCategory
11. Unit
12. Session
13. Cabin
14. User

If you need a different order, modify the `deletion_order` list in the management command.

### Programmatic Cleanup
```python
from django.apps import apps
from bunk_logs.utils.models import TestDataMixin

# Clean up test data for all models
total_deleted = 0
for app_config in apps.get_app_configs():
    for model in app_config.get_models():
        if issubclass(model, TestDataMixin):
            deleted = model.delete_all_test_data()
            if deleted > 0:
                print(f"Deleted {deleted} {model.__name__} records")
                total_deleted += deleted

print(f"Total deleted: {total_deleted}")
```

This test data management system gives you complete control over dummy data in your BunkLogs application, making it easy to import test data for development and demos while keeping your production data clean.

This system provides an easy way to identify and manage dummy/testing data in your BunkLogs application. All models now include an `is_test_data` field that allows you to mark records as test data for easy identification and cleanup.

## Features

- ✅ **Test Data Tracking**: All models inherit from `TestDataMixin` which adds an `is_test_data` boolean field
- ✅ **CSV Import with Test Flag**: Import CSV data and automatically mark it as test data
- ✅ **Admin Interface Integration**: Filter, view, and manage test data directly from Django admin
- ✅ **Bulk Operations**: Mark multiple records as test/production data with admin actions
- ✅ **Easy Cleanup**: Delete all test data with a single management command
- ✅ **Safe Operations**: Dry-run modes and confirmation prompts prevent accidental deletions

## Quick Start

### 1. Importing Test Data from CSV

Import dummy data and mark it as test data:

```bash
# Import test campers
python manage.py import_test_data \
    --csv-file /path/to/test_campers.csv \
    --model campers \
    --test-data

# Import test users
python manage.py import_test_data \
    --csv-file /path/to/test_users.csv \
    --model users \
    --test-data
```

### 2. Viewing Test Data

In Django admin, all models now have:
- **Test Data Filter**: Filter records by "Test Data" or "Production Data"
- **Color-coded Display**: Test data appears in red, production data in green
- **Bulk Actions**: Mark selected items as test/production data

### 3. Cleaning Up Test Data

Preview what would be deleted:
```bash
python manage.py cleanup_test_data
```

Actually delete all test data (with confirmation):
```bash
python manage.py cleanup_test_data --confirm
```

Delete test data from specific app only:
```bash
python manage.py cleanup_test_data --app campers --confirm
```

## CSV Import Examples

### Example CSV Format for Campers

```csv
first_name,last_name,date_of_birth,emergency_contact_name,emergency_contact_phone
John,Doe,2010-05-15,Jane Doe,555-123-4567
Alice,Smith,2011-03-22,Bob Smith,555-987-6543
Test,Camper,2012-01-01,Test Parent,555-000-0000
```

### Example CSV Format for Users

```csv
email,first_name,last_name,role
test.counselor@example.com,Test,Counselor,Counselor
dummy.admin@example.com,Dummy,Admin,Admin
sample.unithead@example.com,Sample,Head,Unit Head
```

### Import Commands

```bash
# Import campers as test data
python manage.py import_test_data \
    --csv-file campers_test.csv \
    --model campers \
    --test-data

# Import users as production data
python manage.py import_test_data \
    --csv-file real_users.csv \
    --model users
```

## Programmatic Usage

### Using the CSV Import Utility

```python
from bunk_logs.utils.csv_import import import_csv_with_test_flag
from bunk_logs.campers.models import Camper

# Define field mapping
field_mapping = {
    'First Name': 'first_name',
    'Last Name': 'last_name', 
    'Email': 'email',
    'Birth Date': 'date_of_birth'
}

# Import with test data flag
result = import_csv_with_test_flag(
    'test_campers.csv',
    Camper,
    field_mapping,
    is_test_data=True,  # Mark as test data
    unique_fields=['email']
)

print(f"Created {result['created']} test records")
```

### Using Model Methods

```python
from bunk_logs.campers.models import Camper

# Get all test data
test_campers = Camper.get_test_data_queryset()

# Get all production data
production_campers = Camper.get_production_data_queryset()

# Delete all test data for this model
deleted_count = Camper.delete_all_test_data()

# Mark existing data as test data
from bunk_logs.utils.csv_import import mark_existing_data_as_test

count = mark_existing_data_as_test(
    Camper, 
    {'first_name__icontains': 'test'}  # Mark campers with 'test' in name
)
```

### Creating Test Data Programmatically

```python
from bunk_logs.campers.models import Camper

# Create a test camper
test_camper = Camper.objects.create(
    first_name="Test",
    last_name="Camper",
    is_test_data=True  # Mark as test data
)

# Create production camper
real_camper = Camper.objects.create(
    first_name="Real",
    last_name="Camper",
    is_test_data=False  # Mark as production data (default)
)
```

## Admin Interface

### Filters and Actions

All admin interfaces now include:

1. **Test Data Filter**: Quick filter to show only test or production data
2. **Bulk Actions**:
   - "Mark selected items as test data"
   - "Mark selected items as production data" 
   - "Delete test data from selection"
3. **Color-coded Display**: Visual distinction between test and production data

### Using Admin Actions

1. Go to any model's admin page (Users, Campers, etc.)
2. Select records you want to modify
3. Choose action from dropdown:
   - Mark as test data
   - Mark as production data
   - Delete test data only
4. Click "Go"

## Best Practices

### 1. Always Mark Imported Test Data

When importing dummy data for testing:
```bash
python manage.py import_test_data --csv-file dummy_data.csv --model campers --test-data
```

### 2. Use Dry Run First

Before importing large datasets:
```bash
python manage.py import_test_data --csv-file data.csv --model users --dry-run
```

### 3. Regular Cleanup

Periodically clean up test data:
```bash
# Check what would be deleted
python manage.py cleanup_test_data

# Delete after review
python manage.py cleanup_test_data --confirm
```

### 4. Filter in Queries

In your application code, filter out test data for production:
```python
# Only get production campers
real_campers = Camper.objects.filter(is_test_data=False)

# Or use the helper method
real_campers = Camper.get_production_data_queryset()
```

## Troubleshooting

### Common Issues

1. **Import Failures**: Check CSV format matches expected field mapping
2. **Permission Errors**: Ensure you have admin permissions to delete test data
3. **Foreign Key Constraints**: Cleanup command handles deletion order automatically

### Getting Help

1. Use `--help` with any management command:
   ```bash
   python manage.py cleanup_test_data --help
   python manage.py import_test_data --help
   ```

2. Check admin interface for visual feedback on test data status

3. Use dry-run modes to preview operations before executing

## Database Schema

The `is_test_data` field has been added to all models:

```sql
-- Example for campers_camper table
ALTER TABLE campers_camper ADD COLUMN is_test_data BOOLEAN NOT NULL DEFAULT FALSE;

-- Index for better query performance (automatically created)
CREATE INDEX campers_camper_is_test_data ON campers_camper (is_test_data);
```

This field is automatically indexed for efficient filtering and querying.
