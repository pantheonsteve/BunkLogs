import csv
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from bunk_logs.bunks.models import Bunk
from bunk_logs.campers.models import CamperBunkAssignment
from bunk_logs.bunklogs.models import BunkLog

User = get_user_model()

class BunkLogImportError(ValueError):
    """Custom exception for bunk log import errors."""
    MISSING_BUNK = "Bunk is required"
    MISSING_CAMPER = "Camper is required"
    MISSING_COUNSELOR = "Counselor is required"
    MISSING_DATE = "Date is required"
    INVALID_DATE = "Invalid date format"
    INVALID_BUNK = "Invalid bunk"
    INVALID_COUNSELOR = "Invalid counselor"
    INVALID_SCORES = "Scores must be between 1 and 5"

def is_valid_date_format(date_str: str) -> bool:
    """Check if the date string is in a valid format (YYYY-MM-DD)."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def _validate_score(score: Optional[str]) -> Optional[int]:
    """Validate that a score is between 1 and 5, or None."""
    if not score or score.strip() == '':
        return None
    
    try:
        score_int = int(score)
        if score_int < 1 or score_int > 5:
            raise BunkLogImportError(BunkLogImportError.INVALID_SCORES)
        return score_int
    except ValueError:
        raise BunkLogImportError(f"Invalid score format: {score}")

def import_bunk_logs_from_csv(file_path: Union[str, Path], *, dry_run: bool = False, default_counselor_email: str = None) -> Dict:
    """
    Imports bunk logs from a CSV file.

    Args:
        file_path: Path to the CSV file
        dry_run: If True, validation is performed but no data is written to database
        default_counselor_email: Email of default counselor to use if not in CSV

    The CSV file should have headers:
    - date (YYYY-MM-DD)
    - camper_first_name
    - camper_last_name
    - bunk (in format "cabin_name - session_name") 
    - counselor_email (email of the counselor) - optional if default_counselor_email is provided
    - not_on_camp (true/false)
    - social_score (1-5 or blank)
    - behavior_score (1-5 or blank)
    - participation_score (1-5 or blank)
    - camper_care_help (true/false)
    - unit_head_help (true/false)
    - description
    
    Returns:
        Dict with success_count, error_count, and errors list
    """
    # Initialize result tracking
    result = {
        "success_count": 0,
        "error_count": 0,
        "errors": []
    }
    
    # Ensure file_path is a string
    if isinstance(file_path, Path):
        file_path = str(file_path)

    # Check if file exists
    if not Path(file_path).exists():
        raise BunkLogImportError(f'File {file_path} does not exist')
    
    # Get default counselor if provided
    default_counselor = None
    if default_counselor_email:
        try:
            default_counselor = User.objects.get(email=default_counselor_email)
        except User.DoesNotExist:
            raise BunkLogImportError(f"Default counselor with email {default_counselor_email} not found")

    with open(file_path, "r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        
        if not reader.fieldnames:
            raise BunkLogImportError("CSV file is empty or has no headers")
        
        # Check for required fields
        required_fields = ['date', 'camper_first_name', 'camper_last_name', 'bunk']
        for field in required_fields:
            if field not in reader.fieldnames:
                raise BunkLogImportError(f"CSV file is missing required field: {field}")
        
        # Process all rows
        for i, row in enumerate(reader):
            try:
                # Extract data from row
                date = row.get("date", "").strip()
                camper_first_name = row.get("camper_first_name", "").strip()
                camper_last_name = row.get("camper_last_name", "").strip()
                bunk_full_name = row.get("bunk", "").strip()  # This is now the full bunk name pattern
                counselor_email = row.get("counselor_email", "").strip()
                
                # Parse boolean fields with defaults
                not_on_camp = row.get("not_on_camp", "").lower() in ["true", "yes", "1", "t", "y"]
                request_camper_care_help = row.get("camper_care_help", "").lower() in ["true", "yes", "1", "t", "y"]
                request_unit_head_help = row.get("unit_head_help", "").lower() in ["true", "yes", "1", "t", "y"]
                
                # Get scores (can be None)
                social_score = row.get("social_score", "").strip() or None
                behavior_score = row.get("behavior_score", "").strip() or None
                participation_score = row.get("participation_score", "").strip() or None
                
                description = row.get("description", "").strip()

                # Validate required fields
                if not all([date, camper_first_name, camper_last_name, bunk_full_name]):
                    missing = []
                    if not date: missing.append("date")
                    if not camper_first_name: missing.append("camper_first_name")
                    if not camper_last_name: missing.append("camper_last_name") 
                    if not bunk_full_name: missing.append("bunk")
                    raise BunkLogImportError(f"Missing required data: {', '.join(missing)}")

                # Handle counselor (either from CSV or default)
                if not counselor_email and not default_counselor:
                    raise BunkLogImportError("Counselor email is required when no default counselor is provided")
                
                # Validate date format
                if not is_valid_date_format(date):
                    raise BunkLogImportError(BunkLogImportError.INVALID_DATE)

                # Parse the bunk name to get cabin and session names
                try:
                    if " - " in bunk_full_name:
                        cabin_name, session_name = bunk_full_name.split(" - ", 1)
                    else:
                        raise ValueError("Bunk name must be in format 'cabin_name - session_name'")
                except ValueError:
                    raise BunkLogImportError(f"Invalid bunk name format: {bunk_full_name}. Expected format: 'cabin_name - session_name'")

                # Find the bunk by cabin and session names
                try:
                    bunk_obj = Bunk.objects.get(
                        cabin__name=cabin_name,
                        session__name=session_name,
                        is_active=True
                    )
                except Bunk.DoesNotExist:
                    # Try to find without checking active status
                    try:
                        bunk_obj = Bunk.objects.get(
                            cabin__name=cabin_name,
                            session__name=session_name
                        )
                        if not bunk_obj.is_active:
                            raise BunkLogImportError(f"Bunk '{bunk_full_name}' exists but is not active")
                    except Bunk.DoesNotExist:
                        raise BunkLogImportError(f"Bunk with cabin '{cabin_name}' and session '{session_name}' does not exist")
                except Bunk.MultipleObjectsReturned:
                    raise BunkLogImportError(f"Multiple active bunks found with cabin '{cabin_name}' and session '{session_name}'")

                # Find the counselor
                try:
                    if counselor_email:
                        counselor = User.objects.get(email=counselor_email)
                    else:
                        counselor = default_counselor
                except User.DoesNotExist:
                    raise BunkLogImportError(f"Counselor with email '{counselor_email}' does not exist")

                # Find the CamperBunkAssignment
                try:
                    bunk_assignment = CamperBunkAssignment.objects.get(
                        camper__first_name__iexact=camper_first_name,
                        camper__last_name__iexact=camper_last_name,
                        bunk=bunk_obj,
                        is_active=True
                    )
                except CamperBunkAssignment.DoesNotExist:
                    raise BunkLogImportError(
                        f"No active assignment found for: {camper_first_name} {camper_last_name} in {bunk_full_name}"
                    )
                except CamperBunkAssignment.MultipleObjectsReturned:
                    raise BunkLogImportError(
                        f"Multiple active assignments found for: {camper_first_name} {camper_last_name} in {bunk_full_name}"
                    )

                # Validate scores
                social_score_int = _validate_score(social_score)
                behavior_score_int = _validate_score(behavior_score)
                participation_score_int = _validate_score(participation_score)

                # Check for existing record
                existing_log = BunkLog.objects.filter(
                    bunk_assignment=bunk_assignment,
                    date=date
                ).first()

                # Create or update BunkLog object
                if not dry_run:
                    if existing_log:
                        # Update existing log
                        existing_log.counselor = counselor
                        existing_log.not_on_camp = not_on_camp
                        existing_log.social_score = social_score_int
                        existing_log.behavior_score = behavior_score_int
                        existing_log.participation_score = participation_score_int
                        existing_log.request_camper_care_help = request_camper_care_help
                        existing_log.request_unit_head_help = request_unit_head_help
                        existing_log.description = description
                        existing_log.save()
                    else:
                        # Create new log
                        BunkLog.objects.create(
                            bunk_assignment=bunk_assignment,
                            date=date,
                            counselor=counselor,
                            not_on_camp=not_on_camp,
                            social_score=social_score_int,
                            behavior_score=behavior_score_int,
                            participation_score=participation_score_int,
                            request_camper_care_help=request_camper_care_help,
                            request_unit_head_help=request_unit_head_help,
                            description=description,
                        )

                result["success_count"] += 1

            except (BunkLogImportError, ValueError) as e:
                # Get basic row info for error reporting
                row_info = {
                    key: row.get(key, "N/A") 
                    for key in ["date", "camper_first_name", "camper_last_name", "bunk", "counselor_email"]
                }
                
                result["error_count"] += 1
                result["errors"].append({
                    "row": i + 2,  # +2 for 1-based indexing and header row
                    "data": row_info,
                    "error": str(e)
                })
                continue

            except Exception as e:
                result["error_count"] += 1
                result["errors"].append({
                    "row": i + 2,
                    "data": {
                        "camper": f"{row.get('camper_first_name', 'N/A')} {row.get('camper_last_name', 'N/A')}",
                        "bunk": row.get('bunk', 'N/A'),
                        "date": row.get('date', 'N/A')
                    },
                    "error": f"Unexpected error: {str(e)}"
                })
                continue

    return result
def generate_sample_csv() -> str:
    """
    Generates a sample CSV file with headers and example data.
    Returns the content as a string.
    """
    headers = [
        "date", "camper_first_name", "camper_last_name", "bunk", 
        "counselor_email", "not_on_camp", "social_score", "behavior_score", 
        "participation_score", "camper_care_help", "unit_head_help", "description"
    ]
    
    sample_row = [
        "2025-03-31", "John", "Smith", "A1", 
        "counselor@example.com", "false", "5", "4", 
        "3", "false", "false", "Had a great day at the lake."
    ]
    
    csv_content = ",".join(headers) + "\n" + ",".join(sample_row)
    return csv_content

def get_expected_columns() -> List[str]:
    """
    Returns a list of expected column headers for the CSV file.
    """
    return [
        "date", "camper_first_name", "camper_last_name", "bunk", 
        "counselor_email", "not_on_camp", "social_score", "behavior_score", 
        "participation_score", "camper_care_help", "unit_head_help", "description"
    ]