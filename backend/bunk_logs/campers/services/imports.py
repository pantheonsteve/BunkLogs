import csv
from pathlib import Path
from typing import Any

from bunk_logs.campers.models import Camper
from bunk_logs.campers.models import CamperBunkAssignment
from django.db import transaction

from bunk_logs.bunks.models import Bunk
from bunk_logs.bunks.models import Cabin
from bunk_logs.bunks.models import Session


class CamperImportError(ValueError):
    """Custom exception for camper import errors."""

    MISSING_FIRST_NAME = "First name is required"
    MISSING_LAST_NAME = "Last name is required"


def _validate_camper_names(first_name: str, last_name: str) -> None:
    """Validate camper names."""
    if not first_name:
        raise CamperImportError(CamperImportError.MISSING_FIRST_NAME)
    if not last_name:
        raise CamperImportError(CamperImportError.MISSING_LAST_NAME)


def import_campers_from_csv(file_path, *, dry_run=False):
    """Import campers from CSV file."""
    success_count = 0
    error_records = []
    file_path = Path(file_path)

    with file_path.open() as csv_file:
        reader = csv.DictReader(csv_file)

        for row in reader:
            try:
                # Data validation
                _validate_row_names(row)

                # Prepare data
                camper_data = {
                    "first_name": row["first_name"],
                    "last_name": row["last_name"],
                    "date_of_birth": row.get("date_of_birth") or None,
                    "emergency_contact_name": row.get("emergency_contact_name") or "",
                    "emergency_contact_phone": row.get("emergency_contact_phone") or "",
                    "camper_notes": row.get("camper_notes") or "",
                    "parent_notes": row.get("parent_notes") or "",
                }

                # Create camper
                camper = Camper(**camper_data)
                if not dry_run:
                    camper.save()

                success_count += 1
            except ValueError as e:
                error_records.append({"row": reader.line_num, "error": str(e)})

    return {
        "success_count": success_count,
        "error_count": len(error_records),
        "errors": error_records,
    }


def _validate_row_names(row: dict[str, str]) -> None:
    """Validate that row has required name fields."""
    if not row.get("first_name"):
        msg = "First name is required"
        raise ValueError(msg)
    if not row.get("last_name"):
        msg = "Last name is required"
        raise ValueError(msg)


class CamperBunkAssignmentError(ValueError):
    """Custom exception for camper bunk assignment import errors."""

    MISSING_CAMPER_NAME = "Camper first and last name are required"
    MISSING_BUNK_NAME = "Bunk name is required"
    MISSING_CABIN_OR_SESSION = "Both cabin name and session name are required"
    CABIN_NOT_FOUND = "Cabin '{0}' not found"
    SESSION_NOT_FOUND = "Session '{0}' not found"
    BUNK_NOT_FOUND = "Bunk with cabin '{0}' and session '{1}' not found"
    MULTIPLE_BUNKS_FOUND = "Multiple bunks found with cabin '{0}' and session '{1}'"
    MULTIPLE_CAMPERS_FOUND = "Multiple campers found with name {0} {1}"


def _validate_camper_bunk_assignment_names(
    camper_first_name: str,
    camper_last_name: str,
    bunk_name: str,
) -> None:
    """Validate camper bunk assignment names."""
    if not camper_first_name or not camper_last_name:
        raise CamperBunkAssignmentError(CamperBunkAssignmentError.MISSING_CAMPER_NAME)
    if not bunk_name:
        raise CamperBunkAssignmentError(CamperBunkAssignmentError.MISSING_BUNK_NAME)


def _validate_names(camper_first_name: str, camper_last_name: str) -> None:
    """Validate that camper names are provided."""
    if not camper_first_name or not camper_last_name:
        raise CamperBunkAssignmentError(CamperBunkAssignmentError.MISSING_CAMPER_NAME)


def _validate_cabin_session(cabin_name: str, session_name: str) -> None:
    """Validate that cabin and session names are provided."""
    if not cabin_name or not session_name:
        error = CamperBunkAssignmentError.MISSING_CABIN_OR_SESSION
        raise CamperBunkAssignmentError(error)


def _find_or_create_camper(
    camper_first_name: str,
    camper_last_name: str,
    *,  # Make dry_run a keyword-only parameter
    dry_run: bool,
) -> Camper:
    """Find existing camper or create a new one if not found."""
    try:
        return Camper.objects.get(
            first_name__iexact=camper_first_name,
            last_name__iexact=camper_last_name,
        )
    except Camper.DoesNotExist:
        # Create a new camper
        camper = Camper(
            first_name=camper_first_name,
            last_name=camper_last_name,
            date_of_birth=None,  # Set to None to avoid validation error
            emergency_contact_name="",
            emergency_contact_phone="",
            camper_notes="",
            parent_notes="",
        )
        if not dry_run:
            camper.save()
        return camper
    except Camper.MultipleObjectsReturned as err:
        error_msg = CamperBunkAssignmentError.MULTIPLE_CAMPERS_FOUND.format(
            camper_first_name,
            camper_last_name,
        )
        raise CamperBunkAssignmentError(error_msg) from err


def _find_cabin(cabin_name: str) -> Cabin:
    """Find cabin by name."""
    try:
        return Cabin.objects.get(name__iexact=cabin_name)
    except Cabin.DoesNotExist as err:
        error_msg = CamperBunkAssignmentError.CABIN_NOT_FOUND.format(cabin_name)
        raise CamperBunkAssignmentError(error_msg) from err


def _find_session(session_name: str) -> Session:
    """Find session by name."""
    try:
        return Session.objects.get(name__iexact=session_name)
    except Session.DoesNotExist as err:
        error_msg = CamperBunkAssignmentError.SESSION_NOT_FOUND.format(session_name)
        raise CamperBunkAssignmentError(error_msg) from err


def _find_bunk(
    cabin: Cabin,
    session: Session,
    cabin_name: str,
    session_name: str,
) -> Bunk:
    """Find bunk by cabin and session."""
    try:
        return Bunk.objects.get(cabin=cabin, session=session)
    except Bunk.DoesNotExist as err:
        error_msg = CamperBunkAssignmentError.BUNK_NOT_FOUND.format(
            cabin_name,
            session_name,
        )
        raise CamperBunkAssignmentError(error_msg) from err
    except Bunk.MultipleObjectsReturned as err:
        error_msg = CamperBunkAssignmentError.MULTIPLE_BUNKS_FOUND.format(
            cabin_name,
            session_name,
        )
        raise CamperBunkAssignmentError(error_msg) from err


def _process_assignment_row(
    row: dict[str, str],
    *,  # Make dry_run a keyword-only parameter
    dry_run: bool,
) -> None:
    """Process a single row of bunk assignment data."""
    # Extract camper information
    camper_first_name = row.get("camper_first_name", "").strip()
    camper_last_name = row.get("camper_last_name", "").strip()
    _validate_names(camper_first_name, camper_last_name)

    # Find or create camper
    camper = _find_or_create_camper(camper_first_name, camper_last_name, dry_run=dry_run)

    # Extract and validate cabin/session
    cabin_name = row.get("cabin_name", "").strip()
    session_name = row.get("session_name", "").strip()
    _validate_cabin_session(cabin_name, session_name)

    # Find cabin, session, and bunk
    cabin = _find_cabin(cabin_name)
    session = _find_session(session_name)
    bunk = _find_bunk(cabin, session, cabin_name, session_name)

    # Parse dates and active status
    start_date = row.get("start_date", "").strip() or None
    end_date = row.get("end_date", "").strip() or None
    is_active = _parse_is_active(row.get("is_active", ""))

    # Create or update assignment if not dry run
    if not dry_run:
        CamperBunkAssignment.objects.update_or_create(
            camper=camper,
            bunk=bunk,
            defaults={
                "start_date": start_date,
                "end_date": end_date,
                "is_active": is_active,
            },
        )


def _parse_is_active(is_active_str: str) -> bool:
    """Parse is_active field from string."""
    is_active_str = is_active_str.strip().lower()
    return is_active_str not in ("false", "0", "no", "n")


def import_bunk_assignments_from_csv(
    file_path: str | Path,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Import camper bunk assignments from CSV file.

    Expected CSV format:
    camper_first_name,camper_last_name,cabin_name,session_name,start_date,end_date,is_active
    """
    success_count = 0
    error_records: list[dict[str, Any]] = []
    file_path = Path(file_path)

    with file_path.open() as csv_file:
        reader = csv.DictReader(csv_file)

        for row in reader:
            # Process each row in its own transaction
            try:
                with transaction.atomic():
                    _process_assignment_row(row, dry_run=dry_run)
                    success_count += 1
            except (ValueError, CamperBunkAssignmentError) as e:
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
