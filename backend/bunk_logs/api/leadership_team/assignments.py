"""LT Template Assignment API (Step 7_12 PR B — Story 52; extended Step 7_20).

Endpoints under ``/api/v1/leadership-team/assignments/``:

* ``POST  /``         — create a new assignment. Detects overlapping
                        assignments on the same ``(template, target)``
                        and requires the body to carry an explicit
                        ``conflict_resolution`` (``"replace"`` /
                        ``"run_both"`` / ``"cancel"``).
* ``PATCH /<id>/``    — only ``end_date`` may be edited once any
                        Reflection responses exist (Story 52 c4/c9).
                        ``is_required`` and ``title`` are also editable
                        when no responses exist. ``assignment_group`` is
                        immutable post-creation (use the replace flow).
* ``DELETE /<id>/``   — cancel a *scheduled* assignment (never started).

Also exposes a helper ``resolve_members(assignment, as_of_date)`` used
internally and by the responses endpoint to materialise the assignment
into a queryset of ``Membership`` rows.
"""

from __future__ import annotations

from datetime import date
from datetime import timedelta
from typing import Any

from django.db import transaction
from django.db.models import Q
from django.utils.dateparse import parse_date
from rest_framework import status as drf_status
from rest_framework.exceptions import NotFound
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core import audit
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import TemplateAssignment

from .common import assignment_viewer_or_403

CONFLICT_CHOICES = ("replace", "run_both", "cancel")
VALID_TARGET_TYPES = ("role", "individuals", "tag_group", "assignment_group")


# ---------------------------------------------------------------------------
# Membership resolution
# ---------------------------------------------------------------------------


def resolve_members(assignment: TemplateAssignment, as_of: date):
    """Return the Memberships that an assignment applies to on ``as_of``.

    * ``role``: dynamic — current active Memberships in the program with
      that role.
    * ``individuals``: static snapshot from ``target_payload['membership_ids']``.
      Filtered to currently active so a deactivated member silently drops.
    * ``tag_group``: dynamic — Memberships whose ``tags`` JSON contains
      the given tag.
    * ``assignment_group``: dynamic — Memberships whose role is in
      template.author_role_filter AND who are active authors in the group.
    """
    payload = assignment.target_payload or {}
    base = Membership.all_objects.filter(
        program=assignment.program, is_active=True,
    )
    target_type = assignment.target_type
    if target_type == TemplateAssignment.TargetType.ROLE:
        role = payload.get("role")
        return base.filter(role=role) if role else base.none()
    if target_type == TemplateAssignment.TargetType.INDIVIDUALS:
        ids = payload.get("membership_ids") or []
        if not isinstance(ids, list):
            return base.none()
        return base.filter(pk__in=ids)
    if target_type == TemplateAssignment.TargetType.TAG_GROUP:
        tag = payload.get("tag")
        if not tag:
            return base.none()
        return base.filter(tags__contains=[tag])
    if target_type == TemplateAssignment.TargetType.ASSIGNMENT_GROUP:
        group_id = assignment.assignment_group_id
        if not group_id:
            return base.none()
        author_roles = assignment.template.author_role_filter or []
        if not author_roles:
            return base.none()
        author_person_ids = AssignmentGroupMembership.all_objects.filter(
            group_id=group_id,
            role_in_group="author",
            is_active=True,
        ).values_list("person_id", flat=True)
        return base.filter(person_id__in=author_person_ids, role__in=author_roles)
    return base.none()


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def _serialize(assignment: TemplateAssignment) -> dict[str, Any]:
    return {
        "id": assignment.id,
        "template": assignment.template_id,
        "template_slug": assignment.template.slug if assignment.template_id else None,
        "target_type": assignment.target_type,
        "target_payload": assignment.target_payload or {},
        "assignment_group": assignment.assignment_group_id,
        "is_required": assignment.is_required,
        "title": assignment.title or "",
        "display_title": assignment.title or (
            assignment.template.name if assignment.template_id else ""
        ),
        "start_date": assignment.start_date.isoformat(),
        "end_date": assignment.end_date.isoformat() if assignment.end_date else None,
        "cadence_override": assignment.cadence_override,
        "status": assignment.status,
        "replaces": assignment.replaces_id,
        "created_at": assignment.created_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate_target(target_type: str, target_payload: dict) -> None:
    if target_type not in VALID_TARGET_TYPES:
        msg = f"target_type must be one of {VALID_TARGET_TYPES}."
        raise ValidationError(msg)
    if target_type == "role" and not target_payload.get("role"):
        msg = "target_payload.role is required for target_type='role'."
        raise ValidationError(msg)
    if target_type == "individuals":
        ids = target_payload.get("membership_ids")
        if not isinstance(ids, list) or not ids:
            msg = "target_payload.membership_ids must be a non-empty list."
            raise ValidationError(msg)
    if target_type == "tag_group" and not target_payload.get("tag"):
        msg = "target_payload.tag is required for target_type='tag_group'."
        raise ValidationError(msg)
    if target_type == "assignment_group":
        # assignment_group_id comes via the dedicated FK column on the
        # request body, not target_payload. Validation happens in the
        # POST handler where we can check DB existence.
        pass


def _targets_equal(a: dict, b: dict) -> bool:
    """Two payloads target the same audience iff their semantic keys match."""
    return (a.get("role") == b.get("role")) and (a.get("tag") == b.get("tag"))


def _find_conflicts(
    *, organization, template: ReflectionTemplate, target_type: str,
    target_payload: dict, start: date, end: date | None,
    assignment_group_id: int | None = None,
):
    """Return queryset of overlapping assignments on (template, target).

    Two assignments conflict iff they share template + target_type +
    target identifiers (role, tag, or assignment_group) AND their date
    windows overlap. Individuals targets are treated as never-overlapping
    (they're explicit per-membership picks).
    """
    if target_type == "individuals":
        return TemplateAssignment.all_objects.none()
    qs = TemplateAssignment.all_objects.filter(
        organization=organization,
        template=template,
        target_type=target_type,
        status__in=[
            TemplateAssignment.Status.SCHEDULED,
            TemplateAssignment.Status.ACTIVE,
        ],
    )
    if target_type == "role":
        qs = qs.filter(target_payload__role=target_payload.get("role"))
    elif target_type == "tag_group":
        qs = qs.filter(target_payload__tag=target_payload.get("tag"))
    elif target_type == "assignment_group":
        qs = qs.filter(assignment_group_id=assignment_group_id)
    end_filter = end or date.max
    return qs.filter(start_date__lte=end_filter).filter(
        Q(end_date__gte=start) | Q(end_date__isnull=True),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


class LeadershipTeamAssignmentListCreateView(APIView):
    """``GET`` lists own-org assignments; ``POST`` creates one."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = assignment_viewer_or_403(request)
        qs = (
            TemplateAssignment.objects
            .filter(organization=ctx.organization)
            .select_related("template")
            .order_by("-start_date", "-created_at")
        )
        template_id = (request.query_params.get("template") or "").strip()
        if template_id.isdigit():
            qs = qs.filter(template_id=int(template_id))
        return Response({"assignments": [_serialize(a) for a in qs[:200]]})

    def post(self, request, *args, **kwargs):
        ctx = assignment_viewer_or_403(request)
        payload = dict(request.data) if isinstance(request.data, dict) else {}

        template_id = payload.get("template")
        if not template_id:
            msg = "template is required."
            raise ValidationError(msg)
        try:
            template = ReflectionTemplate.all_objects.get(pk=template_id)
        except ReflectionTemplate.DoesNotExist as exc:
            msg = "Template not found."
            raise NotFound(msg) from exc
        if (
            template.organization_id is not None
            and template.organization_id != ctx.organization.pk
        ):
            msg = "Cannot assign templates from another organization."
            raise PermissionDenied(msg)
        if template.status != ReflectionTemplate.Status.PUBLISHED:
            msg = "Only published templates can be assigned."
            raise ValidationError(msg)

        target_type = payload.get("target_type") or ""
        target_payload = payload.get("target_payload") or {}
        if not isinstance(target_payload, dict):
            msg = "target_payload must be an object."
            raise ValidationError(msg)
        _validate_target(target_type, target_payload)

        # New fields (Step 7_20).
        assignment_group_id = payload.get("assignment_group")
        is_required = payload.get("is_required", True)
        title = (payload.get("title") or "").strip()

        group: AssignmentGroup | None = None
        if target_type == "assignment_group":
            if not assignment_group_id:
                msg = "assignment_group is required when target_type='assignment_group'."
                raise ValidationError(msg)
            try:
                group = AssignmentGroup.objects.get(
                    pk=assignment_group_id, program=ctx.program,
                )
            except AssignmentGroup.DoesNotExist as exc:
                msg = "AssignmentGroup not found."
                raise NotFound(msg) from exc
        elif assignment_group_id:
            msg = "assignment_group can only be set when target_type='assignment_group'."
            raise ValidationError(msg)

        start = parse_date(payload.get("start_date") or "")
        if start is None:
            msg = "start_date is required (YYYY-MM-DD)."
            raise ValidationError(msg)
        end_raw = payload.get("end_date")
        end = parse_date(end_raw) if end_raw else None
        if end and end < start:
            msg = "end_date must be on or after start_date."
            raise ValidationError(msg)

        conflicts = list(_find_conflicts(
            organization=ctx.organization,
            template=template,
            target_type=target_type,
            target_payload=target_payload,
            start=start,
            end=end,
            assignment_group_id=assignment_group_id,
        ))
        conflict_resolution = (payload.get("conflict_resolution") or "").lower()
        if conflicts and conflict_resolution not in CONFLICT_CHOICES:
            return Response(
                {
                    "detail": "Assignment conflict requires conflict_resolution.",
                    "conflicts": [_serialize(a) for a in conflicts],
                    "choices": list(CONFLICT_CHOICES),
                },
                status=drf_status.HTTP_409_CONFLICT,
            )
        if conflict_resolution == "cancel":
            return Response(
                {"detail": "Cancelled — no assignment created."},
                status=drf_status.HTTP_200_OK,
            )

        with transaction.atomic():
            new_assignment = TemplateAssignment.all_objects.create(
                organization=ctx.organization,
                program=ctx.program,
                template=template,
                target_type=target_type,
                target_payload=target_payload,
                assignment_group=group,
                is_required=is_required,
                title=title,
                start_date=start,
                end_date=end,
                cadence_override=payload.get("cadence_override") or None,
                status=TemplateAssignment.Status.SCHEDULED,
                created_by=ctx.membership,
            )
            if conflict_resolution == "replace" and conflicts:
                stop = start - timedelta(days=1)
                for prior in conflicts:
                    prior.end_date = stop
                    prior.status = TemplateAssignment.Status.ENDED
                    prior.save(update_fields=["end_date", "status"])
                new_assignment.replaces = conflicts[0]
                new_assignment.save(update_fields=["replaces"])

        audit.created(
            actor=request.user,
            content=new_assignment,
            content_type="template_assignment",
            metadata={
                "template_id": template.pk,
                "target_type": target_type,
                "conflict_resolution": conflict_resolution or None,
            },
        )
        return Response(
            _serialize(new_assignment), status=drf_status.HTTP_201_CREATED,
        )


class LeadershipTeamAssignmentDetailView(APIView):
    """``PATCH /<id>/`` — edit allowed fields; ``DELETE /<id>/`` cancels scheduled.

    Always editable: ``end_date``.
    Editable only when no responses exist: ``cadence_override``,
    ``target_payload``, ``is_required``, ``title``.
    Immutable post-creation: ``assignment_group`` (use the replace flow).
    """

    permission_classes = [IsAuthenticated]

    def _get(self, request, pk: int) -> TemplateAssignment:
        ctx = assignment_viewer_or_403(request)
        try:
            return TemplateAssignment.objects.select_related("template").get(
                organization=ctx.organization, pk=pk,
            )
        except TemplateAssignment.DoesNotExist as exc:
            raise NotFound from exc

    def patch(self, request, pk: int, *args, **kwargs):
        assignment = self._get(request, pk)
        payload = dict(request.data) if isinstance(request.data, dict) else {}
        has_responses = Reflection.all_objects.filter(
            template=assignment.template,
            program=assignment.program,
            period_start__gte=assignment.start_date,
        ).exists()

        if "assignment_group" in payload:
            msg = (
                "assignment_group is immutable post-creation. "
                "Use conflict_resolution='replace' to create a new assignment."
            )
            raise ValidationError(msg)

        if has_responses:
            editable = {"end_date"}
            disallowed = set(payload.keys()) - editable
            if disallowed:
                msg = (
                    "Only end_date may be edited after responses exist; "
                    f"got: {sorted(disallowed)}."
                )
                raise ValidationError(msg)

        before = _serialize(assignment)

        if "end_date" in payload:
            new_end = (
                parse_date(payload["end_date"]) if payload["end_date"] else None
            )
            if new_end and new_end < assignment.start_date:
                msg = "end_date must be on or after start_date."
                raise ValidationError(msg)
            assignment.end_date = new_end
        if not has_responses:
            for k in ("cadence_override", "target_payload"):
                if k in payload:
                    setattr(assignment, k, payload[k])
            if "is_required" in payload:
                assignment.is_required = bool(payload["is_required"])
            if "title" in payload:
                assignment.title = (payload["title"] or "").strip()
        assignment.save()

        audit.edited(
            actor=request.user,
            content=assignment,
            before=before,
            after=_serialize(assignment),
            content_type="template_assignment",
        )
        return Response(_serialize(assignment))

    def delete(self, request, pk: int, *args, **kwargs):
        assignment = self._get(request, pk)
        if assignment.status != TemplateAssignment.Status.SCHEDULED:
            msg = "Only scheduled assignments may be cancelled."
            raise ValidationError(msg)
        before = _serialize(assignment)
        assignment.status = TemplateAssignment.Status.CANCELLED
        assignment.save(update_fields=["status"])
        audit.state_changed(
            actor=request.user,
            content=assignment,
            before_state=before["status"],
            after_state=assignment.status,
            content_type="template_assignment",
        )
        return Response(status=drf_status.HTTP_204_NO_CONTENT)
