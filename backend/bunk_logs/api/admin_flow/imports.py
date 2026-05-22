"""Admin bulk-import wrapper (Step 7_13 PR3, Story 55 + supplemental).

Two endpoints:

* ``POST /api/v1/admin/people/import/preview/`` -- accepts a CSV
  + ``source`` (``campminder`` or ``tbe``) + ``program_slug``. Parses
  the CSV in memory and returns a row-by-row diff (additions, changes,
  conflicts) without writing anything.
* ``POST /api/v1/admin/people/import/commit/`` -- accepts the same
  payload and invokes the existing management command
  (``import_campminder_roster`` / ``import_tbe_roster``) inside a
  ``transaction.atomic`` block, then writes a ``RosterImportLog``
  row.

The commit is **idempotent**: re-running the same CSV is a no-op
because the underlying upsert logic in those commands keys on
``external_ids.campminder_id`` / ``external_ids.tbe_id``.
"""

from __future__ import annotations

import csv
import io
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser
from rest_framework.parsers import JSONParser
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import RosterImportLog
from bunk_logs.core.permissions import IsOrgAdminOrSuperuser

from .common import viewer_or_403

SUPPORTED_SOURCES = ("campminder", "tbe")
VALID_ROLES = frozenset(role for role, _ in Membership.ROLES)


def _read_csv_rows(raw_bytes: bytes) -> list[dict]:
    text = raw_bytes.decode("utf-8-sig", errors="replace")
    return list(csv.DictReader(io.StringIO(text)))


def _normalize_external_id(source: str, row: dict) -> str:
    key = f"{source}_id"
    return (row.get(key) or row.get("external_id") or "").strip()


def _classify_row(*, source: str, org, program, row: dict) -> dict:
    """Classify a single CSV row as add / change / skip / conflict."""
    external_id = _normalize_external_id(source, row)
    role = (row.get("role") or "").strip()
    first_name = (row.get("first_name") or "").strip()
    last_name = (row.get("last_name") or "").strip()
    email = (row.get("email") or "").strip()

    issues: list[str] = []
    if not external_id:
        issues.append(f"missing {source}_id")
    if role and role not in VALID_ROLES:
        issues.append(f"unknown role {role!r}")
    if not first_name or not last_name:
        issues.append("missing first_name or last_name")

    classification = "skip" if issues else "noop"
    existing_person = None
    if external_id:
        existing_person = Person.all_objects.filter(
            organization=org,
            external_ids__contains={f"{source}_id": external_id},
        ).first()
    if existing_person is None and email:
        existing_person = Person.all_objects.filter(
            organization=org, email__iexact=email,
        ).first()
        if existing_person is not None:
            issues.append(
                f"email already attached to Person {existing_person.id} "
                f"with no {source}_id — will merge",
            )

    if not issues:
        if existing_person is None:
            classification = "add"
        else:
            changed = []
            if existing_person.first_name != first_name:
                changed.append("first_name")
            if existing_person.last_name != last_name:
                changed.append("last_name")
            if email and existing_person.email != email:
                changed.append("email")
            classification = "change" if changed else "noop"
    elif existing_person is not None:
        classification = "conflict"

    return {
        "external_id": external_id,
        "role": role,
        "full_name": f"{first_name} {last_name}".strip(),
        "email": email,
        "classification": classification,
        "issues": issues,
        "existing_person_id": existing_person.id if existing_person else None,
    }


class AdminBulkImportPreviewView(APIView):
    """Dry-run a Campminder / TBE roster CSV."""

    permission_classes = [IsOrgAdminOrSuperuser]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        source = (request.data.get("source") or "").strip().lower()
        if source not in SUPPORTED_SOURCES:
            return Response(
                {"detail": f"source must be one of {SUPPORTED_SOURCES}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        program_slug = (request.data.get("program_slug") or "").strip()
        try:
            program = Program.all_objects.get(
                organization=ctx.organization, slug=program_slug,
            )
        except Program.DoesNotExist:
            return Response(
                {"detail": f"Program {program_slug!r} not found in this org."},
                status=status.HTTP_404_NOT_FOUND,
            )
        csv_file = request.FILES.get("csv")
        if csv_file is None:
            return Response(
                {"detail": "CSV file is required (multipart field 'csv')."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            rows = _read_csv_rows(csv_file.read())
        except Exception as exc:
            return Response(
                {"detail": f"Could not parse CSV: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        classified = [
            _classify_row(
                source=source, org=ctx.organization, program=program, row=row,
            )
            for row in rows
        ]
        summary = {
            "row_count": len(classified),
            "add": sum(1 for r in classified if r["classification"] == "add"),
            "change": sum(1 for r in classified if r["classification"] == "change"),
            "noop": sum(1 for r in classified if r["classification"] == "noop"),
            "skip": sum(1 for r in classified if r["classification"] == "skip"),
            "conflict": sum(1 for r in classified if r["classification"] == "conflict"),
        }
        return Response({
            "source": source,
            "program": {"id": program.id, "slug": program.slug},
            "summary": summary,
            "rows": classified,
        })


class AdminBulkImportCommitView(APIView):
    """Wrap the existing management command in a transactional API call.

    The command writes its own ``RosterImportLog`` row; we surface its
    pk on the response so the UI can deep-link to the audit history.
    """

    permission_classes = [IsOrgAdminOrSuperuser]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        source = (request.data.get("source") or "").strip().lower()
        if source not in SUPPORTED_SOURCES:
            return Response(
                {"detail": f"source must be one of {SUPPORTED_SOURCES}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        program_slug = (request.data.get("program_slug") or "").strip()
        try:
            program = Program.all_objects.get(
                organization=ctx.organization, slug=program_slug,
            )
        except Program.DoesNotExist:
            return Response(
                {"detail": f"Program {program_slug!r} not found in this org."},
                status=status.HTTP_404_NOT_FOUND,
            )
        csv_file = request.FILES.get("csv")
        if csv_file is None:
            return Response(
                {"detail": "CSV file is required (multipart field 'csv')."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".csv", delete=False,
        ) as tmp:
            tmp.write(csv_file.read())
            tmp_path = Path(tmp.name)
        command_name = (
            "import_campminder_roster" if source == "campminder"
            else "import_tbe_roster"
        )
        before_log_max_id = (
            RosterImportLog.all_objects.filter(
                organization=ctx.organization, program=program,
            )
            .order_by("-id").values_list("id", flat=True).first()
            or 0
        )
        try:
            with transaction.atomic():
                call_command(
                    command_name,
                    csv_path=str(tmp_path),
                    org_slug=ctx.organization.slug,
                    program_slug=program.slug,
                )
        except Exception as exc:
            tmp_path.unlink(missing_ok=True)
            return Response(
                {"detail": f"Import failed: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        tmp_path.unlink(missing_ok=True)
        log = (
            RosterImportLog.all_objects.filter(
                organization=ctx.organization, program=program,
                id__gt=before_log_max_id,
            )
            .order_by("-id").first()
        )
        return Response({
            "status": "completed",
            "completed_at": timezone.now().isoformat(),
            "log": {
                "id": log.id if log else None,
                "summary": log.summary if log else {},
            },
        })
