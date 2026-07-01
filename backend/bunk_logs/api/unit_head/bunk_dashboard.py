"""``GET /api/v1/unit-head/bunks/<bunk_id>/?date=<>`` — Story 11.

Composes the bunk page payload from the per-section primitives. UH
opens this when tapping a bunk from the dashboard; the API is
read-only (Story 11 criterion 5).

Sections returned, all key-named so the frontend can render them in
spec order (criterion 1) and collapse them when empty (criterion 2):

* ``header`` — bunk + date + counselor display names.
* ``help_requested`` — campers who asked for UH help today.
* ``camper_care_help_requested`` — campers who asked for Camper Care help today.
* ``off_camp`` — campers flagged ``is_off_camp`` today.
* ``bunk_concerns`` — counselor / UH self-reflections that referenced
  this bunk via ``bunk_concerns_bunks`` today.
* ``score_grid`` — Story 12 grid (columns + per-camper cells).
* ``orders`` — Story 14: today's Camper Care + Maintenance items
  submitted by counselors authoring this bunk, plus "carried over".
* ``specialist_reports`` — Story 15: visibility-filtered Notes
  authored by Specialists about this bunk's campers.
"""

from __future__ import annotations

from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from typing import TYPE_CHECKING

from django.db.models import Q
from django.utils.dateparse import parse_date
from rest_framework.exceptions import NotFound
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.api.counselor.common import bunk_camper_persons
from bunk_logs.api.counselor.common import camper_reflection_template
from bunk_logs.api.counselor.common import person_display_name
from bunk_logs.api.counselor.common import person_full_name
from bunk_logs.core.filters import reflections_visible_for_user
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import MaintenanceTicket
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Order
from bunk_logs.core.models import Person
from bunk_logs.core.models import Reflection
from bunk_logs.core.permissions.observation_read import filter_observations_readable
from bunk_logs.core.state_machine import OrderStateMachine
from bunk_logs.core.time_utils import get_org_timezone
from bunk_logs.notes.models import Observation

from .common import build_score_grid
from .common import bunk_concerns_referencing
from .common import camper_care_help_requested_camper_ids_from
from .common import counselor_self_reflections_for_bunk
from .common import help_requested_camper_ids_from
from .common import off_camp_camper_ids
from .common import supervised_bunk_ids
from .common import viewer_or_403

if TYPE_CHECKING:
    from zoneinfo import ZoneInfo

OPEN_STATUSES = (OrderStateMachine.NEW, OrderStateMachine.IN_PROGRESS)
RESOLVED_STATUSES = (OrderStateMachine.FULFILLED, OrderStateMachine.UNABLE_TO_FULFILL)


def program_display_name(program, organization=None) -> str | None:
    """Session-friendly program label (drops the org name prefix when present)."""
    if program is None:
        return None
    org_name = ""
    if organization is not None:
        org_name = organization.name
    elif program.organization_id:
        org_name = program.organization.name
    prefix = f"{org_name} - " if org_name else ""
    if prefix and program.name.startswith(prefix):
        return program.name[len(prefix):]
    return program.name


class UnitHeadBunkDashboardView(APIView):
    """Per-bunk read payload for the Unit Head Bunk Dashboard."""

    permission_classes = [IsAuthenticated]

    def get(self, request, bunk_id: int, *args, **kwargs):
        ctx = viewer_or_403(request)
        target_date = _parse_date_param(
            request.query_params.get("date"), default=ctx.today,
        )
        # No future dates (Story 11 criterion 3).
        if target_date > ctx.today:
            msg = "Future dates are not selectable."
            raise ValidationError(msg)

        # Supervision gate: viewer must supervise this bunk (today —
        # the supervision relationship is "as of today", not the
        # selected date, since UH can browse history for bunks they
        # supervise NOW).
        supervised_ids = supervised_bunk_ids(ctx.membership, today=ctx.today)
        if int(bunk_id) not in supervised_ids:
            msg = "You do not supervise this bunk."
            raise PermissionDenied(msg)

        bunk = AssignmentGroup.all_objects.filter(
            id=bunk_id, group_type="bunk", is_active=True,
        ).select_related("parent").first()
        if bunk is None:
            msg = "Bunk not found."
            raise NotFound(msg)

        return Response(build_bunk_dashboard_payload(
            request=request,
            bunk=bunk,
            target_date=target_date,
            organization=ctx.organization,
            program=ctx.program,
            today=ctx.today,
        ))


# ---------------------------------------------------------------------------
# Shared payload builder (role-agnostic; reused by Camper Care 7_8c)
# ---------------------------------------------------------------------------


def build_bunk_dashboard_payload(
    *,
    request,
    bunk: AssignmentGroup,
    target_date: date,
    organization,
    program,
    today: date,
) -> dict:
    """Compose the per-bunk dashboard payload, viewer-visibility-filtered.

    Pulled out of the UH view so Camper Care (7_8c), LT, and Admin
    can call it with their own role-specific viewer + supervision
    gates while sharing the same payload contract. Visibility is
    enforced inside via ``request.user`` so the caller cannot widen
    audience by handing in a different organization or program.
    """
    campers = bunk_camper_persons([bunk]).get(bunk.id, [])
    camper_ids = [c.id for c in campers]

    off_camp = off_camp_camper_ids(organization, target_date, camper_ids)
    off_camp_payload = [
        _camper_brief(c, off_camp=True) for c in campers if c.id in off_camp
    ]

    # Today's camper reflections (visibility-filtered) for help
    # surface + score grid.
    camper_template = camper_reflection_template(
        organization, program, as_of=target_date, bunk=bunk,
    )
    reflections_by_subject: dict[int, Reflection] = {}
    if camper_template is not None and campers:
        visible_qs = reflections_visible_for_user(
            request.user,
            Reflection.all_objects.filter(
                template=camper_template,
                assignment_group=bunk,
                period_start=target_date,
                period_end=target_date,
                is_complete=True,
            ).select_related("template", "author"),
        )
        for r in visible_qs:
            if r.subject_id is not None:
                reflections_by_subject[r.subject_id] = r

    help_ids = help_requested_camper_ids_from(reflections_by_subject)
    help_payload = [
        _camper_brief(c) for c in campers if c.id in help_ids
    ]

    cc_help_ids = camper_care_help_requested_camper_ids_from(reflections_by_subject)
    cc_help_payload = [
        _camper_brief(c) for c in campers if c.id in cc_help_ids
    ]

    # Bunk-concerns referencing this bunk today.
    bc_map = bunk_concerns_referencing(
        organization=organization,
        program=program,
        target_date=target_date,
    )
    bc_payload = _serialize_bunk_concerns(bc_map.get(bunk.id, []))

    # Score grid (Story 12).
    score_grid_payload = (
        build_score_grid(
            template=camper_template,
            campers=campers,
            reflections_by_subject=reflections_by_subject,
        ) if camper_template else {"columns": [], "rows": []}
    )

    # Orders + Maintenance Tickets for the bunk (Story 14).
    orders_payload = _orders_for_bunk(
        bunk=bunk, target_date=target_date, organization=organization,
        program=program,
    )

    # Specialist reports (Story 15) — legacy placeholder; observations below.
    spec_payload = _specialist_reports_for_bunk(
        request=request, camper_ids=camper_ids, target_date=target_date,
    )

    observations_payload = _observations_for_bunk(
        request=request,
        organization=organization,
        program=program,
        target_date=target_date,
        camper_ids=camper_ids,
    )

    counselor_self_payload = counselor_self_reflections_for_bunk(
        request=request, bunk=bunk, target_date=target_date,
    )

    return {
        "header": {
            "bunk": {
                "id": bunk.id,
                "name": bunk.name,
                "slug": bunk.slug,
                "unit_name": (bunk.parent.name if bunk.parent_id else None),
            },
            "program_name": program_display_name(program, organization),
            "date": target_date.isoformat(),
            "today": today.isoformat(),
            "counselor_names": _counselor_names(bunk),
        },
        "help_requested": help_payload,
        "camper_care_help_requested": cc_help_payload,
        "off_camp": off_camp_payload,
        "bunk_concerns": bc_payload,
        "counselor_self_reflections": counselor_self_payload,
        "score_grid": score_grid_payload,
        "orders": orders_payload,
        "specialist_reports": spec_payload,
        "observations": observations_payload,
    }


OBSERVATION_PREVIEW_MAX_LEN = 120


def _observations_for_bunk(
    *,
    request,
    organization,
    program,
    target_date: date,
    camper_ids: list[int],
) -> list[dict]:
    """Observations about bunk campers timestamped on ``target_date`` (org TZ)."""
    if not camper_ids:
        return []

    viewer = Person.objects.filter(user=request.user).first()
    tz = get_org_timezone(organization)
    day_start = datetime.combine(target_date, time.min, tzinfo=tz)
    day_end = day_start + timedelta(days=1)

    base = (
        Observation.all_objects.filter(
            organization=organization,
            program=program,
            subject_links__subject_id__in=camper_ids,
            observed_at__gte=day_start,
            observed_at__lt=day_end,
        )
        .select_related("author")
        .prefetch_related("subject_links__subject")
        .distinct()
    )
    observations = list(
        filter_observations_readable(base, viewer, organization, request.user).order_by(
            "-observed_at",
        ),
    )
    rows: list[dict] = []
    for obs in observations:
        body = obs.body or ""
        preview = (
            body
            if len(body) <= OBSERVATION_PREVIEW_MAX_LEN
            else body[: OBSERVATION_PREVIEW_MAX_LEN - 1] + "…"
        )
        subjects = [
            {"id": link.subject_id, "name": link.subject.full_name}
            for link in obs.subject_links.all()
            if link.subject_id
        ]
        rows.append({
            "id": obs.id,
            "body_preview": preview,
            "author_name": obs.author.full_name if obs.author_id and obs.author else None,
            "subjects": subjects,
            "sensitivity": obs.sensitivity,
            "context": obs.context or "",
            "observed_at": obs.observed_at.isoformat() if obs.observed_at else None,
        })
    return rows


# ---------------------------------------------------------------------------
# Section helpers
# ---------------------------------------------------------------------------


def _parse_date_param(raw: str | None, *, default: date) -> date:
    if not raw:
        return default
    parsed = parse_date(raw)
    if parsed is None:
        msg = "Invalid 'date' parameter; expected YYYY-MM-DD."
        raise ValidationError(msg)
    return parsed


def _camper_brief(camper: Person, *, off_camp: bool = False) -> dict:
    return {
        "id": camper.id,
        "first_name": camper.first_name,
        "last_name": camper.last_name,
        "preferred_name": camper.preferred_name,
        "off_camp": off_camp,
    }


def _counselor_names(bunk: AssignmentGroup) -> list[str]:
    rows = (
        AssignmentGroupMembership.objects.filter(
            group=bunk, role_in_group="author", is_active=True,
        )
        .select_related("person")
        .order_by("person__last_name", "person__first_name")
    )
    return [person_full_name(agm.person) for agm in rows if agm.person]


def _serialize_bunk_concerns(reflections: list[Reflection]) -> list[dict]:
    """Compact payload for the Bunk Concerns section.

    Includes the author's display name, the role binding the template
    targets (counselor vs unit_head — informs how the section header
    labels the source), the linked Reflection id, and the narrative
    note when present.
    """
    out: list[dict] = []
    for r in reflections:
        answers = r.answers or {}
        out.append({
            "reflection_id": r.id,
            "author": person_display_name(r.author),
            "author_role": (r.template.role if r.template_id else None),
            "note": answers.get("bunk_concerns_note") or "",
            "open_concern": answers.get("concern") or "",
            "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
        })
    return out


def _orders_for_bunk(
    *, bunk: AssignmentGroup, target_date: date, organization, program,
) -> dict:
    """Combined Orders + Maintenance Tickets for the bunk.

    Two sub-lists per Story 14 criterion 6: ``today`` and
    ``carried_over``. Carried-over is anything still in an open state
    that was submitted *before* ``target_date``. Status counts are at
    the top so the section header can render "[n] open / [m] in
    progress / [k] resolved" (criterion 4).
    """
    counselor_membership_ids = _counselor_membership_ids_for_bunk(bunk)
    if not counselor_membership_ids:
        return {
            "today": [], "carried_over": [],
            "counts": {"open": 0, "in_progress": 0, "resolved": 0},
        }

    org_tz = get_org_timezone(organization)
    orders = (
        Order.all_objects.filter(
            organization=organization,
            program=program,
            submitted_by_id__in=counselor_membership_ids,
        )
        .filter(_date_window(target_date))
        .select_related("subject", "submitted_by", "submitted_by__person")
        .order_by("-created_at")
    )
    tickets = (
        MaintenanceTicket.all_objects.filter(
            organization=organization,
            program=program,
            submitted_by_id__in=counselor_membership_ids,
        )
        .filter(_date_window(target_date))
        .select_related("submitted_by", "submitted_by__person")
        .order_by("-created_at")
    )

    today_items: list[dict] = []
    carried_over: list[dict] = []
    counts = {"open": 0, "in_progress": 0, "resolved": 0}

    for o in orders:
        item = _serialize_order(o)
        _bucket_request(item, o.created_at, o.status, target_date, today_items, carried_over, tz=org_tz)
        _bucket_count(o.status, counts)
    for t in tickets:
        item = _serialize_ticket(t)
        _bucket_request(item, t.created_at, t.status, target_date, today_items, carried_over, tz=org_tz)
        _bucket_count(t.status, counts)

    today_items.sort(key=lambda r: r["submitted_at"], reverse=True)
    carried_over.sort(key=lambda r: r["submitted_at"], reverse=True)
    return {"today": today_items, "carried_over": carried_over, "counts": counts}


def _date_window(target_date: date):
    """Filter spanning ``target_date`` plus open carry-overs from before.

    Postgres extracts ``created_at__date`` in UTC, but the org's "today"
    is in the org's local timezone, so a row created at, say,
    2026-07-04 02:00 UTC may belong to 2026-07-03 in US Eastern. We
    widen the SQL filter by one UTC day on the high side to capture
    overflow; the Python bucketer (:func:`_bucket_request`) re-checks
    in the org's tz to assign rows to ``today`` vs ``carried_over``.
    """
    return Q(created_at__date__lte=target_date + timedelta(days=1))


def _bucket_request(
    item: dict, submitted_at: datetime, status: str, target_date: date,
    today_items: list[dict], carried_over: list[dict],
    *,
    tz: ZoneInfo | None = None,
) -> None:
    if submitted_at is None:
        submitted_date = target_date
    elif tz is not None and submitted_at.tzinfo is not None:
        submitted_date = submitted_at.astimezone(tz).date()
    else:
        submitted_date = submitted_at.date()
    if submitted_date == target_date:
        today_items.append(item)
    elif submitted_date > target_date:
        # Future relative to org-local today — date_window widened by a
        # UTC day to capture timezone overflow, so a row that's actually
        # *tomorrow* in the org's tz must be dropped.
        return
    elif status in OPEN_STATUSES:
        carried_over.append(item)
    # else: resolved + submitted on a prior date — drop


def _bucket_count(status: str, counts: dict) -> None:
    if status == OrderStateMachine.NEW:
        counts["open"] += 1
    elif status == OrderStateMachine.IN_PROGRESS:
        counts["in_progress"] += 1
    elif status in RESOLVED_STATUSES:
        counts["resolved"] += 1


def _serialize_order(order: Order) -> dict:
    subject = order.subject
    submitter = order.submitted_by.person if order.submitted_by else None
    return {
        "kind": "camper_care",
        "id": str(order.id),
        "status": order.status,
        "urgency": getattr(order, "urgency", None),
        "subject": (
            {
                "id": subject.id,
                "preferred_name": subject.preferred_name,
                "first_name": subject.first_name,
                "last_name": subject.last_name,
            } if subject else None
        ),
        "item": order.item,
        "item_note": order.item_note,
        "submitter": person_display_name(submitter),
        "submitted_at": order.created_at.isoformat() if order.created_at else None,
        "photo_count": 0,  # Orders don't carry photos in 7_6.
    }


def _serialize_ticket(ticket: MaintenanceTicket) -> dict:
    submitter = ticket.submitted_by.person if ticket.submitted_by else None
    return {
        "kind": "maintenance",
        "id": str(ticket.id),
        "status": ticket.status,
        "urgency": getattr(ticket, "urgency", None),
        "location": ticket.location,
        "category": ticket.category,
        "submitter": person_display_name(submitter),
        "submitted_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "photo_count": ticket.photos.count() if hasattr(ticket, "photos") else 0,
    }


def _counselor_membership_ids_for_bunk(bunk: AssignmentGroup) -> list[int]:
    """Active counselor / JC ``Membership`` IDs authoring this bunk.

    We resolve via ``AssignmentGroupMembership`` (the canonical "who
    authors this bunk" relation) then back to their counselor /
    junior_counselor program-Memberships in the same program as the
    bunk. This handles a counselor who has multiple program
    memberships but whose authorship is bound to the specific
    program-Membership that maps to THIS bunk's program.
    """
    person_ids = list(
        AssignmentGroupMembership.objects.filter(
            group=bunk, role_in_group="author", is_active=True,
        ).values_list("person_id", flat=True),
    )
    if not person_ids:
        return []
    return list(
        Membership.objects.filter(
            person_id__in=person_ids,
            program=bunk.program_id,
            role__in=("counselor", "junior_counselor"),
            is_active=True,
        ).values_list("id", flat=True),
    )


def _specialist_reports_for_bunk(
    *, request, camper_ids: list[int], target_date: date,
) -> dict:
    """Placeholder until bunk dashboard consumes Observations (Step 7_23)."""
    return {"today": [], "recent": [], "sensitive_counts_by_camper": {}}
