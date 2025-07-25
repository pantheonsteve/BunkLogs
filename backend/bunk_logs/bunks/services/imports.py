import csv
from pathlib import Path
from typing import Any
from datetime import datetime

from bunk_logs.users.models import User  # Adjust based on your actual model
from bunk_logs.bunks.models import Bunk  # Adjust based on your actual model
from bunk_logs.bunks.models import Cabin  # Adjust based on your actual model
from bunk_logs.bunks.models import Session  # Adjust based on your actual model
from bunk_logs.bunks.models import Unit  # Adjust based on your actual model
from bunk_logs.bunks.models import CounselorBunkAssignment


class UnitImportError(ValueError):
    """Custom exception for unit import errors."""

    MISSING_NAME = "Unit name is required"


def _validate_unit_name(name: str) -> None:
    """Validate unit name."""
    if not name:
        raise UnitImportError(UnitImportError.MISSING_NAME)


def import_units_from_csv(file_path, *, dry_run=False):
    """Import units from CSV file."""

    success_count = 0
    error_records = []
    file_path = Path(file_path)

    with file_path.open() as csv_file:
        reader = csv.DictReader(csv_file)

        for row in reader:
            try:
                # Data validation
                _validate_unit_name(row.get("name", ""))

                # Prepare data
                unit_data = {
                    "name": row["name"],
                }

                # Look up unit head by email or username if provided
                unit_head_identifier = row.get("unit_head_email") or row.get(
                    "unit_head_username",
                )
                unit_head = None

                if unit_head_identifier:
                    # Try email first
                    if "@" in unit_head_identifier:
                        unit_head = User.objects.filter(
                            email=unit_head_identifier,
                            role="UNIT_HEAD",
                        ).first()
                    else:
                        # Then try username
                        unit_head = User.objects.filter(
                            username=unit_head_identifier,
                            role="UNIT_HEAD",
                        ).first()

                    if not unit_head:
                        unit_data["unit_head"] = (
                            None  # Will be None anyway, but explicit
                        )
                    else:
                        unit_data["unit_head"] = unit_head

                # In dry run mode, we validate but don't save
                if not dry_run:
                    # Create or update unit
                    unit, created = Unit.objects.update_or_create(
                        name=row["name"],
                        defaults=unit_data,
                    )

                success_count += 1
            except (ValueError, TypeError, KeyError) as e:
                error_records.append(
                    {
                        "row": row,
                        "error": str(e),
                    },
                )

    return {
        "success_count": success_count,
        "error_count": len(error_records),
        "errors": error_records,
    }


class CabinImportError(ValueError):
    """Custom exception for cabin import errors."""

    MISSING_NAME = "Cabin name is required"


def _validate_cabin_name(name: str) -> None:
    """Validate cabin name."""
    if not name:
        raise CabinImportError(CabinImportError.MISSING_NAME)


def import_cabins_from_csv(
    file_path: str | Path,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Import cabins from CSV file.

    Args:
        file_path: Path to the CSV file
        dry_run: If True, validate the data without saving to database

    Returns:
        Dictionary with import results
    """
    success_count = 0
    error_records: list[dict[str, Any]] = []

    file_path = Path(file_path)

    with file_path.open() as csv_file:
        reader = csv.DictReader(csv_file)

        for row in reader:
            try:
                # Data validation
                name = row.get("name", "")
                _validate_cabin_name(name)

                # Transform data if needed
                capacity = int(row.get("capacity", 0))

                # In dry run mode, we validate but don't save
                if not dry_run:
                    # Create or update cabin
                    cabin, created = Cabin.objects.update_or_create(
                        name=row["name"],
                        defaults={
                            "capacity": capacity,
                            "location": row.get("location", ""),
                            "notes": row.get("notes", ""),  # Matches your model
                            # Add other fields as needed
                        },
                    )

                success_count += 1
            except (ValueError, TypeError, KeyError) as e:
                error_records.append(
                    {
                        "row": row,
                        "error": str(e),
                    },
                )

    return {
        "success_count": success_count,
        "error_count": len(error_records),
        "errors": error_records,
    }


class BunkImportError(ValueError):
    """Custom exception for bunk import errors."""

    MISSING_NAME = "Bunk name is required"
    INVALID_UNIT = "Unit does not exist"
    MISSING_CABIN = "Missing cabin name"
    MISSING_UNIT = "Missing unit name"
    MISSING_SESSION = "Missing session name"
    CABIN_NOT_FOUND = "Cabin '{0}' does not exist"
    UNIT_NOT_FOUND = "Unit '{0}' does not exist"
    SESSION_NOT_FOUND = "Session '{0}' does not exist"


def _get_or_create_cabin(cabin_name, *, dry_run=False):
    """Get or create a cabin by name."""
    if not cabin_name.strip():
        raise BunkImportError(BunkImportError.MISSING_CABIN)

    cabin_name = cabin_name.strip()
    try:
        return Cabin.objects.get(name=cabin_name), False
    except Cabin.DoesNotExist as err:
        if not dry_run:
            return Cabin.objects.create(name=cabin_name), True
        raise BunkImportError(
            BunkImportError.CABIN_NOT_FOUND.format(cabin_name),
        ) from err


def _get_unit(unit_name):
    """Get a unit by name."""
    if not unit_name.strip():
        raise BunkImportError(BunkImportError.MISSING_UNIT)

    unit_name = unit_name.strip()
    try:
        return Unit.objects.get(name=unit_name)
    except Unit.DoesNotExist as err:
        raise BunkImportError(BunkImportError.UNIT_NOT_FOUND.format(unit_name)) from err


def _get_session(session_name):
    """Get a session by name."""
    if not session_name.strip():
        raise BunkImportError(BunkImportError.MISSING_SESSION)

    session_name = session_name.strip()
    try:
        return Session.objects.get(name=session_name)
    except Session.DoesNotExist as err:
        raise BunkImportError(
            BunkImportError.SESSION_NOT_FOUND.format(session_name),
        ) from err


def _process_bunk_row(row, *, dry_run=False):
    """Process a single row from the CSV file."""
    cabin_name = row.get("cabin", "").strip()
    cabin_instance, cabin_created = _get_or_create_cabin(cabin_name, dry_run=dry_run)

    unit_name = row.get("unit", "").strip()
    unit_instance = _get_unit(unit_name)

    session_name = row.get("session", "").strip()
    session_instance = _get_session(session_name)

    is_active_str = row.get("is_active", "true").lower().strip()
    is_active = is_active_str != "false"  # Default to True unless explicitly "false"

    if not dry_run:
        bunk, created = Bunk.objects.update_or_create(
            cabin=cabin_instance,
            session=session_instance,
            defaults={"unit": unit_instance, "is_active": is_active},
        )
        return {"created": created, "cabin_created": cabin_created, "bunk": bunk}

    return {"cabin_created": cabin_created}


def import_bunks_from_csv(file_path, *, dry_run=False):
    """Import bunks from CSV file."""
    results = {
        "created": 0,
        "updated": 0,
        "errors": [],
        "created_cabins": 0,
    }

    try:
        file_path = Path(file_path)
        with file_path.open(encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file)

            for row_num, row in enumerate(reader, start=1):
                try:
                    row_result = _process_bunk_row(row, dry_run=dry_run)

                    if not dry_run:
                        if row_result["created"]:
                            results["created"] += 1
                        else:
                            results["updated"] += 1

                        if row_result["cabin_created"]:
                            results["created_cabins"] += 1

                except BunkImportError as e:
                    results["errors"].append(f"Row {row_num}: {e!s}")
                except (ValueError, KeyError, TypeError) as e:
                    results["errors"].append(f"Error in row {row_num}: {e!s}")

    except (OSError, FileNotFoundError, PermissionError) as e:
        results["errors"].append(f"File error: {e!s}")

    return results


class CounselorBunkAssignmentImportError(ValueError):
    """Custom exception for counselor bunk assignment import errors."""

    MISSING_COUNSELOR_EMAIL = "Counselor email is required"
    MISSING_BUNK_INFO = "Bunk information is required (cabin_name and session_name)"
    COUNSELOR_NOT_FOUND = "Counselor not found"
    BUNK_NOT_FOUND = "Bunk not found"
    INVALID_DATE_FORMAT = "Invalid date format. Use YYYY-MM-DD"
    INVALID_PRIMARY_VALUE = "Invalid is_primary value. Use 'true', 'false', '1', or '0'"


def _validate_counselor_assignment_data(row: dict) -> None:
    """Validate counselor bunk assignment data."""
    if not row.get("counselor_email", "").strip():
        raise CounselorBunkAssignmentImportError(CounselorBunkAssignmentImportError.MISSING_COUNSELOR_EMAIL)

    if not (row.get("cabin_name", "").strip() and row.get("session_name", "").strip()):
        raise CounselorBunkAssignmentImportError(CounselorBunkAssignmentImportError.MISSING_BUNK_INFO)


def _parse_date(date_str: str) -> datetime.date:
    """Parse date string in YYYY-MM-DD format."""
    if not date_str or not date_str.strip():
        return None

    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise CounselorBunkAssignmentImportError(CounselorBunkAssignmentImportError.INVALID_DATE_FORMAT)


def _parse_boolean(value: str) -> bool:
    """Parse boolean value from string."""
    if not value or not value.strip():
        return False

    value = value.strip().lower()
    if value in ('true', '1', 'yes', 'y'):
        return True
    elif value in ('false', '0', 'no', 'n'):
        return False
    else:
        raise CounselorBunkAssignmentImportError(CounselorBunkAssignmentImportError.INVALID_PRIMARY_VALUE)


def import_counselor_bunk_assignments_from_csv(file_path, *, dry_run=False):
    """
    Import counselor bunk assignments from CSV file.

    Expected CSV columns:
    - counselor_email (required): Email of the counselor
    - cabin_name (required): Name of the cabin
    - session_name (required): Name of the session
    - start_date (required): Start date in YYYY-MM-DD format
    - end_date (optional): End date in YYYY-MM-DD format (blank for ongoing)
    - is_primary (optional): 'true'/'false' or '1'/'0' - whether this is the primary counselor
    """

    results = {
        "success_count": 0,
        "created": 0,
        "updated": 0,
        "errors": [],
        "warnings": [],
    }

    try:
        file_path = Path(file_path)

        with file_path.open(encoding='utf-8') as csv_file:
            reader = csv.DictReader(csv_file)

            for row_num, row in enumerate(reader, start=2):  # Start at 2 because row 1 is headers
                try:
                    # Validate required data
                    _validate_counselor_assignment_data(row)

                    # Find counselor
                    counselor_email = row["counselor_email"].strip()
                    try:
                        counselor = User.objects.get(email=counselor_email, role="Counselor")
                    except User.DoesNotExist:
                        raise CounselorBunkAssignmentImportError(
                            f"{CounselorBunkAssignmentImportError.COUNSELOR_NOT_FOUND}: {counselor_email}"
                        )

                    # Find bunk
                    cabin_name = row["cabin_name"].strip()
                    session_name = row["session_name"].strip()
                    try:
                        bunk = Bunk.objects.get(
                            cabin__name=cabin_name,
                            session__name=session_name
                        )
                    except Bunk.DoesNotExist:
                        raise CounselorBunkAssignmentImportError(
                            f"{CounselorBunkAssignmentImportError.BUNK_NOT_FOUND}: {cabin_name} - {session_name}"
                        )

                    # Parse dates
                    start_date = _parse_date(row.get("start_date", ""))
                    if not start_date:
                        # Default to today if no start date provided
                        from django.utils import timezone
                        start_date = timezone.now().date()

                    end_date = _parse_date(row.get("end_date", ""))

                    # Parse is_primary
                    is_primary = _parse_boolean(row.get("is_primary", "false"))

                    # Prepare assignment data
                    assignment_data = {
                        "counselor": counselor,
                        "bunk": bunk,
                        "start_date": start_date,
                        "end_date": end_date,
                        "is_primary": is_primary,
                    }

                    if not dry_run:
                        # Check if assignment already exists
                        existing_assignment = CounselorBunkAssignment.objects.filter(
                            counselor=counselor,
                            bunk=bunk,
                            start_date=start_date,
                        ).first()

                        if existing_assignment:
                            # Update existing assignment
                            existing_assignment.end_date = end_date
                            existing_assignment.is_primary = is_primary
                            existing_assignment.save()
                            results["updated"] += 1
                        else:
                            # Create new assignment
                            CounselorBunkAssignment.objects.create(**assignment_data)
                            results["created"] += 1

                    results["success_count"] += 1

                except CounselorBunkAssignmentImportError as e:
                    results["errors"].append(f"Row {row_num}: {e}")
                except Exception as e:
                    results["errors"].append(f"Row {row_num}: Unexpected error - {e}")

    except (OSError, FileNotFoundError, PermissionError) as e:
        results["errors"].append(f"File error: {e}")
    except Exception as e:
        results["errors"].append(f"Unexpected error: {e}")

    return results


def import_unit_staff_assignments_from_csv(file_path, *, dry_run=False):
    """Import unit staff assignments from CSV file."""
    import csv
    from bunk_logs.users.models import User
    from bunk_logs.bunks.models import Unit, UnitStaffAssignment
    from datetime import datetime

    success_count = 0
    error_records = []
    file_path = Path(file_path)

    with file_path.open(encoding='utf-8') as csv_file:
        reader = csv.DictReader(csv_file)
        for row_num, row in enumerate(reader, start=2):
            try:
                staff_email = row.get("staff_email", "").strip()
                unit_name = row.get("unit_name", "").strip()
                role = row.get("role", "").strip()
                is_primary = row.get("is_primary", "").strip().lower() == "true"
                start_date = row.get("start_date", "").strip()
                end_date = row.get("end_date", "").strip()

                if not staff_email or not unit_name or not role or not start_date:
                    raise ValueError("Missing required fields: staff_email, unit_name, role, start_date")

                try:
                    staff_member = User.objects.get(email=staff_email)
                except User.DoesNotExist:
                    raise ValueError(f"Staff member with email '{staff_email}' not found")

                try:
                    unit = Unit.objects.get(name=unit_name)
                except Unit.DoesNotExist:
                    raise ValueError(f"Unit with name '{unit_name}' not found")

                # Parse dates
                start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
                end_date_obj = None
                if end_date:
                    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()

                if not dry_run:
                    assignment, created = UnitStaffAssignment.objects.update_or_create(
                        unit=unit,
                        staff_member=staff_member,
                        role=role,
                        defaults={
                            "is_primary": is_primary,
                            "start_date": start_date_obj,
                            "end_date": end_date_obj,
                        },
                    )
                success_count += 1
            except Exception as e:
                error_records.append({"row": row_num, "error": str(e)})

    return {
        "success_count": success_count,
        "error_count": len(error_records),
        "errors": error_records,
    }
