"""``GET /api/v1/unit-head/bunks/<bunk_id>/?date=<>`` — Story 11.

Composes the bunk page payload from the per-section primitives. UH
opens this when tapping a bunk from the dashboard; the API is
read-only (Story 11 criterion 5).

Sections returned, all key-named so the frontend can render them in
spec order (criterion 1) and collapse them when empty (criterion 2):

* ``header`` — bunk + date + counselor display names.
* ``help_requested`` — campers who asked for UH help today.
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

from typing import TYPE_CHECKING

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
from bunk_logs.core.filters import notes_visible_to
from bunk_logs.core.filters import reflections_visible_for_user
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import MaintenanceTicket
from bunk_logs.core.models import Note
from bunk_logs.core.models import Order
from bunk_logs.core.models import Person
from bunk_logs.core.models import Reflection
from bunk_logs.core.state_machine import OrderStateMachine

from .common import build_score_grid
from .common import bunk_concerns_referencing
from .common import help_requested_camper_ids_from
from .common import off_camp_camper_ids
from .common import supervised_bunk_ids
from .common import viewer_or_403

if TYPE_CHECKING:
    from datetime import date
    from datetime import datetime

OPEN_STATUSES = (OrderStateMachine.NEW, OrderStateMachine.IN_PROGRESS)
RESOLVED_STATUSES = (OrderStateMachine.FULFILLED, OrderStateMachine.UNABLE_TO_FULFILL)


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

        campers = bunk_camper_persons([bunk]).get(bunk.id, [])
        camper_ids = [c.id for c in campers]

        off_camp = off_camp_camper_ids(ctx.organization, target_date, camper_ids)
        off_camp_payload = [
            _camper_brief(c, off_camp=True) for c in campers if c.id in off_camp
        ]

        # Today's camper reflections (visibility-filtered) for help
        # surface + score grid.
        camper_template = camper_reflection_template(ctx.organization, ctx.program)
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

        # Bunk-concerns referencing this bunk today.
        bc_map = bunk_concerns_referencing(
            organization=ctx.organization,
            program=ctx.program,
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
            bunk=bunk, target_date=target_date, organization=ctx.organization,
            program=ctx.program,
        )

        # Specialist reports (Story 15).
        spec_payload = _specialist_reports_for_bunk(
            request=request, camper_ids=camper_ids, target_date=target_date,
        )

        return Response({
            "header": {
                "bunk": {
                    "id": bunk.id,
                    "name": bunk.name,
                    "slug": bunk.slug,
                    "unit_name": (bunk.parent.name if bunk.parent_id else None),
                },
                "date": target_date.isoformat(),
                "today": ctx.today.isoformat(),
                "counselor_names": _counselor_names(bunk),
            },
            "help_requested": help_payload,
            "off_camp": off_camp_payload,
            "bunk_concerns": bc_payload,
            "score_grid": score_grid_payload,
            "orders": orders_payload,
            "specialist_reports": spec_payload,
        })


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
    return [person_display_name(agm.person) for agm in rows if agm.person]


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
        _bucket_request(item, o.created_at, o.status, target_date, today_items, carried_over)
        _bucket_count(o.status, counts)
    for t in tickets:
        item = _serialize_ticket(t)
        _bucket_request(item, t.created_at, t.status, target_date, today_items, carried_over)
        _bucket_count(t.status, counts)

    today_items.sort(key=lambda r: r["submitted_at"], reverse=True)
    carried_over.sort(key=lambda r: r["submitted_at"], reverse=True)
    return {"today": today_items, "carried_over": carried_over, "counts": counts}


def _date_window(target_date: date):
    """Filter spanning ``target_date`` plus open carry-overs from before.

    We need rows submitted ON ``target_date`` AND rows submitted
    before that are still open. The simplest correct filter is "any
    row whose date <= target_date AND (date == target_date OR status
    is open)". We materialize both conditions in the Python loop
    rather than at SQL level so the carried-over bucket can include
    arbitrarily old rows without an unbounded date range.
    """
    from django.db.models import Q
    return Q(created_at__date__lte=target_date)


def _bucket_request(
    item: dict, submitted_at: datetime, status: str, target_date: date,
    today_items: list[dict], carried_over: list[dict],
) -> None:
    submitted_date = submitted_at.date() if submitted_at else target_date
    if submitted_date == target_date:
        today_items.append(item)
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
    from bunk_logs.core.models import Membership as _Membership
    return list(
        _Membership.objects.filter(
            person_id__in=person_ids,
            program=bunk.program_id,
            role__in=("counselor", "junior_counselor"),
            is_active=True,
        ).values_list("id", flat=True),
    )


def _specialist_reports_for_bunk(
    *, request, camper_ids: list[int], target_date: date,
) -> dict:
    """Visibility-filtered specialist notes for the bunk's campers.

    Story 15 splits today vs recent (14-day cap). Sensitive notes are
    excluded by ``notes_visible_to``; the placeholder count is
    surfaced per camper so the frontend can render "1 sensitive note"
    (Story 15 criterion 4).
    """
    from datetime import timedelta
    if not camper_ids:
        return {"today": [], "recent": [], "sensitive_counts_by_camper": {}}

    cutoff = target_date - timedelta(days=14)

    base = Note.all_objects.filter(
        note_type=Note.NoteType.SPECIALIST,
        subject_id__in=camper_ids,
        created_at__date__lte=target_date,
        created_at__date__gte=cutoff,
    ).select_related("subject", "author")

    visible = notes_visible_to(request.user, base)
    visible_ids = set(visible.values_list("id", flat=True))

    today_rows: list[dict] = []
    recent_rows: list[dict] = []
    for n in visible.order_by("-created_at"):
        body = n.body or ""
        preview = body if len(body) <= 200 else (body[:200].rstrip() + "…")
        item = {
            "id": n.id,
            "subject": {
                "id": n.subject_id,
                "first_name": n.subject.first_name if n.subject else "",
                "last_name": n.subject.last_name if n.subject else "",
                "preferred_name": n.subject.preferred_name if n.subject else "",
            },
            "author": person_display_name(n.author),
            "created_at": n.created_at.isoformat(),
            "body": body,
            "preview": preview,
            "is_long": len(body) > 200,
            "is_sensitive": bool(n.is_sensitive),
        }
        if n.created_at.date() == target_date:
            today_rows.append(item)
        else:
            recent_rows.append(item)

    # Sensitive count per camper for the placeholder pill.
    sensitive_counts: dict[int, int] = {}
    for row in base.exclude(id__in=visible_ids).filter(is_sensitive=True):
        sensitive_counts[row.subject_id] = sensitive_counts.get(row.subject_id, 0) + 1

    return {
        "today": today_rows,
        "recent": recent_rows,
        "sensitive_counts_by_camper": sensitive_counts,
    }
