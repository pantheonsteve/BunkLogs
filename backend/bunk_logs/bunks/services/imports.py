import csv
from pathlib import Path
from typing import Any

from bunk_logs.users.models import User  # Adjust based on your actual model
from bunks.models import Bunk  # Adjust based on your actual model
from bunks.models import Cabin  # Adjust based on your actual model
from bunks.models import Session  # Adjust based on your actual model
from bunks.models import Unit  # Adjust based on your actual model


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
