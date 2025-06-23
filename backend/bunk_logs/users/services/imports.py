import csv
import time
from pathlib import Path
from typing import Any

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import transaction

from bunk_logs.users.models import User


class UserImportError(ValueError):
    """Custom exception for user import errors."""

    MISSING_EMAIL = "Email is required"
    MISSING_FIRST_NAME = "First name is required"
    MISSING_LAST_NAME = "Last name is required"
    INVALID_EMAIL = "Invalid email format"
    INVALID_ROLE = "Invalid role. Must be one of: Admin, Camper Care, Unit Head, Counselor"
    DUPLICATE_EMAIL = "User with this email already exists"


def _validate_user_data(row: dict[str, str]) -> None:
    """Validate user data from CSV row."""
    email = row.get("email", "").strip()
    first_name = row.get("first_name", "").strip()
    last_name = row.get("last_name", "").strip()
    role = row.get("role", "").strip()

    if not email:
        raise UserImportError(UserImportError.MISSING_EMAIL)
    
    if not first_name:
        raise UserImportError(UserImportError.MISSING_FIRST_NAME)
    
    if not last_name:
        raise UserImportError(UserImportError.MISSING_LAST_NAME)
    
    # Basic email validation
    if "@" not in email or "." not in email:
        raise UserImportError(UserImportError.INVALID_EMAIL)
    
    # Validate role if provided
    if role and role not in [choice[0] for choice in User.ROLE_CHOICES]:
        raise UserImportError(UserImportError.INVALID_ROLE)


def import_users_from_csv(file_path, *, dry_run=False, batch_size=25, use_fast_hashing=True):
    """
    Import users from CSV file with optimizations for large datasets.
    
    Expected CSV format:
    email,first_name,last_name,role,password,is_active,is_staff
    
    Args:
        file_path: Path to the CSV file
        dry_run: If True, validate the data without saving to database
        batch_size: Number of users to process per batch (default: 25)
        use_fast_hashing: Use faster password hashing for bulk imports
        
    Returns:
        Dictionary with import results
    """
    success_count = 0
    error_records = []
    file_path = Path(file_path)
    
    # Optimize password hashing for bulk operations
    original_hashers = None
    if use_fast_hashing and not dry_run:
        original_hashers = settings.PASSWORD_HASHERS
        # Use PBKDF2 which is faster than Argon2 for bulk operations
        settings.PASSWORD_HASHERS = [
            'django.contrib.auth.hashers.PBKDF2PasswordHasher',
            'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
        ] + settings.PASSWORD_HASHERS

    try:
        with file_path.open() as csv_file:
            reader = csv.DictReader(csv_file)
            
            # Convert to list to enable batching
            rows = list(reader)
            total_rows = len(rows)
            
            # Process in batches
            for batch_start in range(0, total_rows, batch_size):
                batch_end = min(batch_start + batch_size, total_rows)
                batch_rows = rows[batch_start:batch_end]
                
                # Process batch within a single transaction
                with transaction.atomic():
                    for row_num, row in enumerate(batch_rows, start=batch_start + 1):
                        try:
                            # Data validation
                            _validate_user_data(row)

                            email = row["email"].strip()
                            first_name = row["first_name"].strip()
                            last_name = row["last_name"].strip()
                            role = row.get("role", "Counselor").strip() or "Counselor"  # Default to Counselor
                            password = row.get("password", "").strip()
                            is_active = row.get("is_active", "true").lower() in ["true", "yes", "1", "t", "y"]
                            is_staff = row.get("is_staff", "false").lower() in ["true", "yes", "1", "t", "y"]

                            # Check for existing user
                            if User.objects.filter(email=email).exists():
                                raise UserImportError(f"{UserImportError.DUPLICATE_EMAIL}: {email}")

                            # Prepare user data
                            user_data = {
                                "email": email,
                                "first_name": first_name,
                                "last_name": last_name,
                                "role": role,
                                "is_active": is_active,
                                "is_staff": is_staff,
                            }

                            # Handle password
                            if password:
                                user_data["password"] = make_password(password)
                            else:
                                # Generate a random password if none provided
                                import secrets
                                import string
                                random_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
                                user_data["password"] = make_password(random_password)

                            # Create user
                            if not dry_run:
                                user = User.objects.create(**user_data)

                            success_count += 1

                        except UserImportError as e:
                            error_records.append({
                                "row": row_num,
                                "error": str(e)
                            })
                        except Exception as e:
                            error_records.append({
                                "row": row_num,
                                "error": f"Unexpected error: {str(e)}"
                            })
                
                # Small delay between batches to prevent overwhelming the system
                if not dry_run and batch_end < total_rows:
                    time.sleep(0.1)
    
    finally:
        # Restore original password hashers
        if original_hashers is not None:
            settings.PASSWORD_HASHERS = original_hashers

    return {
        "success_count": success_count,
        "error_count": len(error_records),
        "errors": error_records,
    }
