# Counselor Bunk Assignment CSV Import

## Overview
This feature allows you to import counselor bunk assignments in bulk using a CSV file through the Django admin interface.

## Access
1. Log into the Django admin interface
2. Navigate to **Bunks > Counselor bunk assignments**
3. Click the **"Import from CSV"** button in the top-right corner

## CSV Format

### Required Columns
- `counselor_email`: Email address of the counselor (must exist in the system with role "Counselor")
- `cabin_name`: Name of the cabin (must exist in the system)
- `session_name`: Name of the session (must exist in the system)
- `start_date`: Start date of the assignment in YYYY-MM-DD format

### Optional Columns
- `end_date`: End date of the assignment in YYYY-MM-DD format (leave blank for ongoing assignments)
- `is_primary`: Whether this counselor is the primary counselor for the bunk (true/false, 1/0, yes/no)

### Sample CSV
```csv
counselor_email,cabin_name,session_name,start_date,end_date,is_primary
john.doe@example.com,Cabin A,Summer 2025,2025-06-15,2025-08-15,true
jane.smith@example.com,Cabin B,Summer 2025,2025-06-15,,false
mike.wilson@example.com,Cabin A,Summer 2025,2025-07-01,2025-07-31,false
```

## Import Process

### Dry Run (Recommended)
1. Check the **"Dry run"** checkbox before importing
2. This will validate your data without making any changes
3. Review any error messages and fix your CSV file as needed

### Actual Import
1. Uncheck the **"Dry run"** checkbox
2. Upload your CSV file
3. Click **"Import"**

## Business Rules

### Update vs Create
- If an assignment already exists for the same counselor, bunk, and start date, it will be **updated**
- Otherwise, a new assignment will be **created**

### Validation
- The counselor must exist and have the role "Counselor"
- The bunk must exist (combination of cabin and session must be valid)
- Start date is required
- End date must be after start date (if provided)
- Only one counselor can be primary for a bunk during overlapping time periods

## Error Handling
- The import will process all valid rows and report errors for invalid ones
- Common errors include:
  - Counselor not found or wrong role
  - Bunk not found (invalid cabin/session combination)
  - Invalid date formats
  - Date range conflicts for primary counselors

## Tips
- Always use the dry run feature first to catch errors
- Ensure counselors and bunks exist before importing assignments
- Use consistent date formatting (YYYY-MM-DD)
- Consider the time periods when assigning primary counselors to avoid conflicts
