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

import tempfile
from pathlib import Path

from django.core.management import call_command
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser
from rest_framework.parsers import JSONParser
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.campminder_csv import IMPORT_TEMPLATE_VARIANTS
from bunk_logs.core.campminder_csv import build_import_template_csv
from bunk_logs.core.campminder_csv import list_import_template_variants
from bunk_logs.core.campminder_csv import normalize_campminder_row
from bunk_logs.core.campminder_csv import read_campminder_csv_bytes
from bunk_logs.core.campminder_person_match import MatchStrategy
from bunk_logs.core.campminder_person_match import match_campminder_person
from bunk_logs.core.campminder_person_match import strategy_is_duplicate
from bunk_logs.core.campminder_user_link import UserLinkAction
from bunk_logs.core.campminder_user_link import preview_user_link
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import RosterImportLog
from bunk_logs.core.permissions import IsOrgAdminOrSuperuser

from .common import viewer_or_403

SUPPORTED_SOURCES = ("campminder", "tbe")
VALID_ROLES = frozenset(role for role, _ in Membership.ROLES)


def _normalize_row(source: str, row: dict) -> dict:
    if source == "campminder":
        return normalize_campminder_row(row)
    return row


def _normalize_external_id(source: str, row: dict) -> str:
    key = f"{source}_id"
    return (row.get(key) or row.get("external_id") or "").strip()


def _classify_row(*, source: str, org, program, row: dict) -> dict:
    """Classify a single CSV row as add / change / merge / duplicate / skip."""
    row = _normalize_row(source, row)
    external_id = _normalize_external_id(source, row)
    role = (row.get("role") or "").strip()
    first_name = (row.get("first_name") or "").strip()
    last_name = (row.get("last_name") or "").strip()
    preferred_name = (row.get("preferred_name") or "").strip()
    email = (row.get("email") or "").strip()

    issues: list[str] = []
    if not external_id:
        issues.append(f"missing {source}_id")
    if role and role not in VALID_ROLES:
        issues.append(f"unknown role {role!r}")
    if not last_name:
        issues.append("missing last_name")
    if not first_name:
        issues.append("missing first_name or preferred_name")

    classification = "skip"
    existing_person = None
    merge_reason = None
    candidate_person_ids: list[int] = []

    if issues:
        return _row_preview_payload(
            external_id=external_id,
            role=role,
            first_name=first_name,
            last_name=last_name,
            email=email,
            row=row,
            classification=classification,
            issues=issues,
            existing_person=None,
            merge_reason=merge_reason,
            candidate_person_ids=candidate_person_ids,
        )

    if source == "campminder":
        person_match = match_campminder_person(
            org,
            campminder_id=external_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
        )
        existing_person = person_match.person
        merge_reason = person_match.strategy.value
        candidate_person_ids = person_match.candidate_ids

        if strategy_is_duplicate(person_match.strategy):
            classification = "duplicate"
            if person_match.strategy == MatchStrategy.DUPLICATE_AMBIGUOUS_NAME:
                issues.append(
                    f"ambiguous name match — {len(candidate_person_ids)} existing "
                    f"persons without Campminder ID",
                )
            elif person_match.strategy == MatchStrategy.DUPLICATE_EMAIL_CONFLICT:
                issues.append(
                    f"email already linked to Person {candidate_person_ids[0]} "
                    f"with a different Campminder ID",
                )
            elif person_match.strategy == MatchStrategy.DUPLICATE_NAME_DIFFERENT_ID:
                issues.append(
                    f"same name as Person {candidate_person_ids[0]} with a "
                    f"different Campminder ID — will create new person",
                )
                classification = "add"
        elif person_match.strategy == MatchStrategy.NEW:
            classification = "add"
        elif person_match.strategy in {
            MatchStrategy.MERGE_EMAIL,
            MatchStrategy.MERGE_NAME,
        }:
            classification = "merge"
            issues.append(
                f"will merge Campminder ID onto existing Person "
                f"{existing_person.id} via {person_match.strategy.value}",
            )
        elif existing_person is not None:
            changed = []
            if existing_person.first_name != first_name:
                changed.append("first_name")
            if existing_person.last_name != last_name:
                changed.append("last_name")
            if preferred_name and existing_person.preferred_name != preferred_name:
                changed.append("preferred_name")
            if email and existing_person.email != email:
                changed.append("email")
            if email and not existing_person.email:
                changed.append("email")
            classification = "change" if changed else "noop"
    else:
        if email:
            existing_person = Person.all_objects.filter(
                organization=org, email__iexact=email,
            ).first()
        classification = "add" if existing_person is None else "noop"

    return _row_preview_payload(
        external_id=external_id,
        role=role,
        first_name=first_name,
        last_name=last_name,
        email=email,
        row=row,
        classification=classification,
        issues=issues,
        existing_person=existing_person,
        merge_reason=merge_reason,
        candidate_person_ids=candidate_person_ids,
    )


def _row_preview_payload(
    *,
    external_id: str,
    role: str,
    first_name: str,
    last_name: str,
    email: str,
    row: dict,
    classification: str,
    issues: list[str],
    existing_person,
    merge_reason,
    candidate_person_ids: list[int],
) -> dict:
    user_link = preview_user_link(
        email=email,
        membership_role=role,
        existing_person=existing_person,
    )
    if user_link.action == UserLinkAction.CREATED:
        issues.append("will create login user")
    elif user_link.action == UserLinkAction.LINKED:
        issues.append(f"will link existing login user {user_link.user_id}")
    elif user_link.action == UserLinkAction.CONFLICT:
        issues.append(f"user link conflict — {user_link.message}")

    return {
        "external_id": external_id,
        "role": role,
        "full_name": f"{first_name} {last_name}".strip(),
        "email": email,
        "position_type": (row.get("position_type") or "").strip(),
        "position": (row.get("position") or "").strip(),
        "classification": classification,
        "issues": issues,
        "existing_person_id": existing_person.id if existing_person else None,
        "merge_reason": merge_reason,
        "candidate_person_ids": candidate_person_ids,
        "user_link_action": user_link.action.value,
        "user_id": user_link.user_id,
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
            rows = read_campminder_csv_bytes(csv_file.read())
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
            "merge": sum(1 for r in classified if r["classification"] == "merge"),
            "noop": sum(1 for r in classified if r["classification"] == "noop"),
            "skip": sum(1 for r in classified if r["classification"] == "skip"),
            "duplicate": sum(1 for r in classified if r["classification"] == "duplicate"),
            "conflict": sum(1 for r in classified if r["classification"] == "conflict"),
            "users_to_create": sum(
                1 for r in classified if r.get("user_link_action") == UserLinkAction.CREATED.value
            ),
            "users_to_link": sum(
                1 for r in classified if r.get("user_link_action") == UserLinkAction.LINKED.value
            ),
        }
        return Response({
            "source": source,
            "program": {"id": program.id, "slug": program.slug},
            "summary": summary,
            "rows": classified,
        })


class AdminBulkImportTemplateView(APIView):
    """Downloadable CSV templates or JSON metadata for bulk people import."""

    permission_classes = [IsOrgAdminOrSuperuser]

    def get(self, request, *args, **kwargs):
        viewer_or_403(request)
        source = (request.query_params.get("source") or "campminder").strip().lower()
        if source != "campminder":
            return Response(
                {"detail": "Templates are only available for source=campminder."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        variant = (request.query_params.get("variant") or "").strip().lower()
        if not variant:
            return Response({
                "source": source,
                "templates": list_import_template_variants(),
            })
        if variant not in IMPORT_TEMPLATE_VARIANTS:
            return Response(
                {
                    "detail": (
                        f"Unknown variant {variant!r}. "
                        f"Choose one of: {', '.join(IMPORT_TEMPLATE_VARIANTS)}."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        filename, csv_text = build_import_template_csv(variant)
        response = HttpResponse(csv_text, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


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
