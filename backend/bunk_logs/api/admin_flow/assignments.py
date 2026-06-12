"""Admin Assignments unified API (Step 7_13 PR2, Story 56).

Single ``/api/v1/admin/assignments/`` surface that fans out across five
relationship types via a ``sub_tab`` query / body parameter:

* ``uh_counselor``    -- :class:`Supervision` with
                         ``target_type=MEMBERSHIP``
* ``cc_caseload``     -- :class:`Supervision` with
                         ``target_type=BUNK``
* ``lt_team``         -- :class:`Supervision` with
                         ``target_type=ROLE_IN_PROGRAM``
* ``counselor_bunk``  -- :class:`AssignmentGroupMembership` (Counselor
                         membership added to a Bunk as ``role_in_group='author'``)
* ``staff_team``      -- :class:`AssignmentGroupMembership` (staff member
                         added to a Team group as ``role_in_group='author'``)
* ``camper_bunk``     -- :class:`AssignmentGroupMembership` (Camper /
                         Student membership added as ``role_in_group='subject'``)

Behavioural invariants enforced server-side:

* Story 56 c4 + A4 -- backdated assignments do NOT retroactively
  reattribute historical content. The endpoint silently records the
  earliest *effective* start date (clamped to today) on the underlying
  row, so historical reflections / supervisions stay anchored to whoever
  authored them. The original ``start_date`` is preserved in
  ``metadata.requested_start_date`` for auditability.
* Story 56 c9 -- overlapping supervisions surface as a ``warnings``
  array on the create response (they don't block).
"""

from __future__ import annotations

from datetime import date

from django.db import transaction
from django.db.models import Q
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core import audit as audit_module
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Supervision
from bunk_logs.core.permissions import IsOrgAdminOrSuperuser

from .common import viewer_or_403

SUPERVISION_SUB_TABS = {
    "uh_counselor": Supervision.TargetType.MEMBERSHIP,
    "cc_caseload": Supervision.TargetType.BUNK,
    "lt_team": Supervision.TargetType.ROLE_IN_PROGRAM,
}
GROUP_SUB_TABS = {"counselor_bunk", "staff_team", "camper_bunk", "uh_unit"}
VALID_SUB_TABS = set(SUPERVISION_SUB_TABS) | GROUP_SUB_TABS


def _coerce_date(raw, fallback: date | None = None) -> date | None:
    if not raw:
        return fallback
    if isinstance(raw, date):
        return raw
    return parse_date(str(raw)) or fallback


def _serialize_supervision(s: Supervision) -> dict:
    target_name = None
    if s.target_type == Supervision.TargetType.MEMBERSHIP:
        target_name = _person_name(s.target_membership)
    elif s.target_type == Supervision.TargetType.BUNK and s.target_bunk_id:
        target_name = s.target_bunk.name if s.target_bunk else None
    elif s.target_type == Supervision.TargetType.ROLE_IN_PROGRAM:
        role = s.target_role or ""
        prog = s.target_program.name if s.target_program_id else ""
        target_name = f"{role} in {prog}".strip() if role or prog else None
    return {
        "id": s.id,
        "kind": "supervision",
        "sub_tab": _sub_tab_for_supervision(s),
        "supervisor_membership_id": s.supervisor_membership_id,
        "supervisor_name": _person_name(s.supervisor_membership),
        "target_type": s.target_type,
        "target_membership_id": s.target_membership_id,
        "target_membership_name": _person_name(s.target_membership),
        "target_role": s.target_role or None,
        "target_program_id": s.target_program_id,
        "target_program_name": s.target_program.name if s.target_program_id else None,
        "target_bunk_id": s.target_bunk_id,
        "target_bunk_name": s.target_bunk.name if s.target_bunk_id else None,
        "target_name": target_name,
        "supervisor_role": (
            s.supervisor_membership.role if s.supervisor_membership_id else None
        ),
        "target_membership_role": (
            s.target_membership.role if s.target_membership_id else None
        ),
        "start_date": s.start_date.isoformat() if s.start_date else None,
        "end_date": s.end_date.isoformat() if s.end_date else None,
        "is_active": s.is_active(),
    }


def _sub_tab_for_supervision(s: Supervision) -> str:
    for tab, ttype in SUPERVISION_SUB_TABS.items():
        if s.target_type == ttype:
            return tab
    return "unknown"


def _sub_tab_for_group_membership(g: AssignmentGroupMembership) -> str:
    if g.role_in_group == "subject":
        return "camper_bunk"
    if g.group_id and g.group.group_type == "team":
        return "staff_team"
    if g.group_id and g.group.group_type == "unit":
        return "uh_unit"
    return "counselor_bunk"


def _membership_role_lookup(
    agms: list[AssignmentGroupMembership],
) -> dict[tuple[int, int], str]:
    """Map (person_id, program_id) to the person's active program membership role."""
    person_ids = {g.person_id for g in agms if g.person_id}
    program_ids = {
        g.group.program_id for g in agms if g.group_id and g.group.program_id
    }
    if not person_ids or not program_ids:
        return {}
    lookup: dict[tuple[int, int], str] = {}
    for membership in Membership.all_objects.filter(
        person_id__in=person_ids,
        program_id__in=program_ids,
        is_active=True,
    ).order_by("person_id", "program_id", "id"):
        key = (membership.person_id, membership.program_id)
        lookup.setdefault(key, membership.role)
    return lookup


def _serialize_group_membership(
    g: AssignmentGroupMembership,
    *,
    membership_roles: dict[tuple[int, int], str] | None = None,
) -> dict:
    program_id = g.group.program_id if g.group_id else None
    membership_role = None
    if membership_roles and g.person_id and program_id:
        membership_role = membership_roles.get((g.person_id, program_id))
    return {
        "id": g.id,
        "kind": "group_membership",
        "sub_tab": _sub_tab_for_group_membership(g),
        "group_id": g.group_id,
        "group_name": g.group.name if g.group_id else None,
        "group_type": g.group.group_type if g.group_id else None,
        "program_id": program_id,
        "person_id": g.person_id,
        "person_name": g.person.full_name if g.person_id else None,
        "role_in_group": g.role_in_group,
        "membership_role": membership_role,
        "start_date": g.start_date.isoformat() if g.start_date else None,
        "end_date": g.end_date.isoformat() if g.end_date else None,
        "is_active": g.is_active,
        "metadata": g.metadata or {},
    }


def _parse_list_filters(request, *, today: date) -> tuple[int | None, str, str, date]:
    program_raw = (request.query_params.get("program") or "").strip()
    program_id = int(program_raw) if program_raw.isdigit() else None
    status = (request.query_params.get("status") or "active").strip().lower()
    if status not in {"active", "ended", "all"}:
        status = "active"
    search = (request.query_params.get("search") or "").strip()
    as_of = _coerce_date(request.query_params.get("as_of"), today)
    return program_id, status, search, as_of


def _apply_supervision_filters(
    qs,
    *,
    program_id: int | None,
    status: str,
    search: str,
    as_of: date,
    sub_tab: str | None,
):
    if program_id is not None:
        if sub_tab == "uh_counselor":
            qs = qs.filter(
                Q(supervisor_membership__program_id=program_id)
                | Q(target_membership__program_id=program_id),
            )
        elif sub_tab == "cc_caseload":
            qs = qs.filter(target_bunk__program_id=program_id)
        elif sub_tab == "lt_team":
            qs = qs.filter(target_program_id=program_id)
        else:
            qs = qs.filter(
                Q(supervisor_membership__program_id=program_id)
                | Q(target_bunk__program_id=program_id)
                | Q(target_program_id=program_id),
            )
    if status == "active":
        qs = qs.active(today=as_of)
    elif status == "ended":
        active_ids = qs.active(today=as_of).values_list("id", flat=True)
        qs = qs.exclude(id__in=active_ids)
    if search:
        qs = qs.filter(
            Q(supervisor_membership__person__first_name__icontains=search)
            | Q(supervisor_membership__person__last_name__icontains=search)
            | Q(target_membership__person__first_name__icontains=search)
            | Q(target_membership__person__last_name__icontains=search)
            | Q(target_bunk__name__icontains=search)
            | Q(target_role__icontains=search),
        )
    return qs.distinct()


def _apply_group_membership_filters(
    qs,
    *,
    program_id: int | None,
    status: str,
    search: str,
):
    if program_id is not None:
        qs = qs.filter(group__program_id=program_id)
    if status == "active":
        qs = qs.filter(is_active=True)
    elif status == "ended":
        qs = qs.filter(is_active=False)
    if search:
        qs = qs.filter(
            Q(person__first_name__icontains=search)
            | Q(person__last_name__icontains=search)
            | Q(group__name__icontains=search),
        )
    return qs.distinct()


def _person_name(membership: Membership | None) -> str | None:
    if membership is None or membership.person_id is None:
        return None
    return membership.person.full_name


class AdminAssignmentsListCreateView(APIView):
    """GET (list) + POST (create) across all five sub-tabs."""

    permission_classes = [IsOrgAdminOrSuperuser]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        sub_tab = (request.query_params.get("sub_tab") or "").strip()
        if sub_tab and sub_tab not in VALID_SUB_TABS:
            return Response(
                {"detail": f"Unknown sub_tab {sub_tab!r}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        program_id, status_filter, search, as_of = _parse_list_filters(
            request, today=ctx.today,
        )

        results: list[dict] = []
        if not sub_tab or sub_tab in SUPERVISION_SUB_TABS:
            qs = Supervision.objects.select_related(
                "supervisor_membership__person", "target_membership__person",
                "target_program", "target_bunk",
            )
            if sub_tab:
                qs = qs.filter(target_type=SUPERVISION_SUB_TABS[sub_tab])
            qs = _apply_supervision_filters(
                qs,
                program_id=program_id,
                status=status_filter,
                search=search,
                as_of=as_of,
                sub_tab=sub_tab or None,
            )
            results.extend(
                _serialize_supervision(s)
                for s in qs.order_by("-start_date", "-created_at")[:500]
            )
        if not sub_tab or sub_tab in GROUP_SUB_TABS:
            qs = AssignmentGroupMembership.objects.select_related("group", "person")
            if sub_tab == "counselor_bunk":
                qs = qs.filter(role_in_group="author", group__group_type="bunk")
            elif sub_tab == "staff_team":
                qs = qs.filter(role_in_group="author", group__group_type="team")
            elif sub_tab == "camper_bunk":
                qs = qs.filter(role_in_group="subject", group__group_type__in=("bunk", "classroom"))
            elif sub_tab == "uh_unit":
                qs = qs.filter(role_in_group="author", group__group_type="unit")
            qs = _apply_group_membership_filters(
                qs,
                program_id=program_id,
                status=status_filter,
                search=search,
            )
            agms = list(qs.order_by("group__name", "person__last_name")[:500])
            role_lookup = _membership_role_lookup(agms)
            results.extend(
                _serialize_group_membership(g, membership_roles=role_lookup)
                for g in agms
            )
        return Response({"results": results})

    def post(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        sub_tab = (request.data.get("sub_tab") or "").strip()
        if sub_tab not in VALID_SUB_TABS:
            return Response(
                {"detail": "sub_tab is required (one of: " + ", ".join(sorted(VALID_SUB_TABS)) + ")."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if sub_tab in SUPERVISION_SUB_TABS:
            return _create_supervision(ctx, request, sub_tab)
        return _create_group_membership(ctx, request, sub_tab)


# ---------------------------------------------------------------------------
# Supervision create / patch
# ---------------------------------------------------------------------------


def _create_supervision(ctx, request, sub_tab: str) -> Response:
    target_type = SUPERVISION_SUB_TABS[sub_tab]
    sup_id = request.data.get("supervisor_membership_id")
    sup = _resolve_membership(ctx, sup_id)
    if sup is None:
        return Response(
            {"detail": "Valid supervisor_membership_id is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    requested_start = _coerce_date(request.data.get("start_date"), ctx.today)
    effective_start = requested_start
    backdated = requested_start < ctx.today
    if backdated:
        effective_start = ctx.today
    end_date = _coerce_date(request.data.get("end_date"), None)

    target_membership = None
    target_role = ""
    target_program = None
    target_bunk = None
    if target_type == Supervision.TargetType.MEMBERSHIP:
        target_membership = _resolve_membership(ctx, request.data.get("target_membership_id"))
        if target_membership is None:
            return Response(
                {"detail": "target_membership_id is required for uh_counselor."},
                status=status.HTTP_400_BAD_REQUEST,
            )
    elif target_type == Supervision.TargetType.BUNK:
        target_bunk = _resolve_assignment_group(ctx, request.data.get("target_bunk_id"))
        if target_bunk is None:
            return Response(
                {"detail": "target_bunk_id is required for cc_caseload."},
                status=status.HTTP_400_BAD_REQUEST,
            )
    elif target_type == Supervision.TargetType.ROLE_IN_PROGRAM:
        target_role = (request.data.get("target_role") or "").strip()
        target_program = _resolve_program(ctx, request.data.get("target_program_id"))
        if not target_role or target_program is None:
            return Response(
                {"detail": "target_role and target_program_id are required for lt_team."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    with transaction.atomic():
        supervision = Supervision(
            supervisor_membership=sup,
            target_type=target_type,
            target_membership=target_membership,
            target_role=target_role,
            target_program=target_program,
            target_bunk=target_bunk,
            start_date=effective_start,
            end_date=end_date,
        )
        try:
            supervision.save()
        except Exception as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        actor = ctx.membership or request.user
        meta = {}
        if backdated:
            meta["requested_start_date"] = requested_start.isoformat()
            meta["backdated_clamp"] = "Historical content remains anchored to original assignments."
        audit_module.created(
            actor, supervision, content_type="supervision",
            after_state={
                "supervisor_membership_id": supervision.supervisor_membership_id,
                "target_type": supervision.target_type,
                "start_date": supervision.start_date.isoformat(),
                "end_date": supervision.end_date.isoformat() if supervision.end_date else None,
            },
            metadata=meta or None,
        )

    warnings = _conflict_warnings_for_supervision(supervision)
    return Response(
        {
            "supervision": _serialize_supervision(supervision),
            "warnings": warnings,
            "backdated_clamped": backdated,
            "requested_start_date": requested_start.isoformat() if backdated else None,
        },
        status=status.HTTP_201_CREATED,
    )


def _conflict_warnings_for_supervision(supervision: Supervision) -> list[dict]:
    """Surface overlapping supervisions on the same target (not blocking).

    Story 56 c9 -- the conflict warning is a soft heuristic the UI
    renders next to the new row so a co-supervisor situation is
    obvious.
    """
    overlap = Supervision.all_objects.filter(
        target_type=supervision.target_type,
    ).exclude(pk=supervision.pk).filter(
        target_membership_id=supervision.target_membership_id,
        target_role=supervision.target_role,
        target_program_id=supervision.target_program_id,
        target_bunk_id=supervision.target_bunk_id,
    )
    return [
        {
            "supervision_id": s.id,
            "supervisor_membership_id": s.supervisor_membership_id,
            "supervisor_name": _person_name(s.supervisor_membership),
            "kind": "co_supervisor",
        }
        for s in overlap.select_related("supervisor_membership__person")[:10]
    ]


# ---------------------------------------------------------------------------
# AssignmentGroupMembership create / patch
# ---------------------------------------------------------------------------


def _create_group_membership(ctx, request, sub_tab: str) -> Response:
    group = _resolve_assignment_group(ctx, request.data.get("group_id"))
    if group is None:
        return Response(
            {"detail": "Valid group_id is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    person = _resolve_person(ctx, request.data.get("person_id"))
    if person is None:
        return Response(
            {"detail": "Valid person_id is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if sub_tab == "camper_bunk":
        role_in_group = "subject"
    else:
        role_in_group = "author"

    mismatch = _group_sub_tab_mismatch(group, sub_tab)
    if mismatch:
        return Response({"detail": mismatch}, status=status.HTTP_400_BAD_REQUEST)

    requested_start = _coerce_date(request.data.get("start_date"), ctx.today)
    effective_start = requested_start
    backdated = requested_start < ctx.today
    if backdated:
        effective_start = ctx.today

    if AssignmentGroupMembership.all_objects.filter(
        group=group, person=person, role_in_group=role_in_group,
    ).exists():
        return Response(
            {"detail": "Person already assigned to this group with this role."},
            status=status.HTTP_409_CONFLICT,
        )
    meta = dict(request.data.get("metadata") or {})
    if backdated:
        meta.update({
            "requested_start_date": requested_start.isoformat(),
            "backdated_clamp": "Historical content remains anchored to original assignments.",
        })
    with transaction.atomic():
        membership = AssignmentGroupMembership.all_objects.create(
            group=group,
            person=person,
            role_in_group=role_in_group,
            start_date=effective_start,
            end_date=_coerce_date(request.data.get("end_date")),
            is_active=request.data.get("is_active", True),
            metadata=meta,
        )
        actor = ctx.membership or request.user
        audit_module.created(
            actor, membership, content_type="assignment_group_membership",
            after_state={
                "group_id": membership.group_id,
                "person_id": membership.person_id,
                "role_in_group": membership.role_in_group,
                "start_date": membership.start_date.isoformat() if membership.start_date else None,
            },
        )
    return Response(
        {
            "assignment_group_membership": _serialize_group_membership(membership),
            "backdated_clamped": backdated,
            "requested_start_date": requested_start.isoformat() if backdated else None,
        },
        status=status.HTTP_201_CREATED,
    )


# ---------------------------------------------------------------------------
# Detail (PATCH) -- soft-end only
# ---------------------------------------------------------------------------


class AdminAssignmentDetailView(APIView):
    """PATCH `/admin/assignments/<id>/?kind=supervision|group_membership`."""

    permission_classes = [IsOrgAdminOrSuperuser]

    def patch(self, request, assignment_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        kind = (request.query_params.get("kind") or request.data.get("kind") or "").strip()
        if kind == "supervision":
            return self._patch_supervision(ctx, request, assignment_id)
        if kind == "group_membership":
            return self._patch_group_membership(ctx, request, assignment_id)
        return Response(
            {"detail": "kind must be 'supervision' or 'group_membership'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def _patch_supervision(self, ctx, request, pk) -> Response:
        try:
            s = Supervision.all_objects.select_related(
                "supervisor_membership__person", "supervisor_membership__program",
            ).get(pk=pk)
        except (Supervision.DoesNotExist, ValueError):
            return Response({"detail": "Supervision not found."}, status=status.HTTP_404_NOT_FOUND)
        if s.supervisor_membership.program.organization_id != ctx.organization.id:
            return Response({"detail": "Supervision not found."}, status=status.HTTP_404_NOT_FOUND)
        if "end_date" not in request.data:
            return Response(
                {"detail": "Only end_date may be patched on a Supervision."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        before = {
            "end_date": s.end_date.isoformat() if s.end_date else None,
        }
        s.end_date = _coerce_date(request.data.get("end_date"))
        s.save(update_fields=["end_date"])
        after = {"end_date": s.end_date.isoformat() if s.end_date else None}
        actor = ctx.membership or request.user
        if s.end_date is not None:
            audit_module.deactivated(
                actor, s,
                before_state=before, after_state=after,
                content_type="supervision",
                reason=(request.data.get("reason") or "").strip(),
            )
        else:
            audit_module.edited(actor, s, before, after, content_type="supervision")
        return Response(_serialize_supervision(s))

    def _patch_group_membership(self, ctx, request, pk) -> Response:
        try:
            g = AssignmentGroupMembership.all_objects.select_related(
                "group", "person",
            ).get(pk=pk)
        except (AssignmentGroupMembership.DoesNotExist, ValueError):
            return Response(
                {"detail": "AssignmentGroupMembership not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if g.group.organization_id != ctx.organization.id:
            return Response(
                {"detail": "AssignmentGroupMembership not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        before = {
            "end_date": g.end_date.isoformat() if g.end_date else None,
            "is_active": g.is_active,
        }
        changed: list[str] = []
        if "end_date" in request.data:
            g.end_date = _coerce_date(request.data.get("end_date"))
            changed.append("end_date")
        if "is_active" in request.data:
            g.is_active = bool(request.data.get("is_active"))
            changed.append("is_active")
        if changed:
            g.save(update_fields=changed)
        after = {
            "end_date": g.end_date.isoformat() if g.end_date else None,
            "is_active": g.is_active,
        }
        actor = ctx.membership or request.user
        if g.is_active is False:
            audit_module.deactivated(
                actor, g,
                before_state=before, after_state=after,
                content_type="assignment_group_membership",
                reason=(request.data.get("reason") or "").strip(),
            )
        else:
            audit_module.edited(
                actor, g, before, after,
                content_type="assignment_group_membership",
            )
        return Response(_serialize_group_membership(g))


def _group_sub_tab_mismatch(group: AssignmentGroup, sub_tab: str) -> str | None:
    """Return an error message when ``group`` does not match ``sub_tab``."""
    if sub_tab == "counselor_bunk" and group.group_type != "bunk":
        return "counselor_bunk assignments require a bunk group."
    if sub_tab == "staff_team" and group.group_type != "team":
        return "staff_team assignments require a team group."
    if sub_tab == "camper_bunk" and group.group_type not in ("bunk", "classroom"):
        return "camper_bunk assignments require a bunk or classroom group."
    if sub_tab == "uh_unit" and group.group_type != "unit":
        return "uh_unit assignments require a unit group."
    return None


# ---------------------------------------------------------------------------
# Resolvers
# ---------------------------------------------------------------------------


def _resolve_membership(ctx, raw) -> Membership | None:
    if raw in (None, ""):
        return None
    try:
        return Membership.all_objects.select_related("program", "person").get(
            pk=raw, program__organization=ctx.organization,
        )
    except (Membership.DoesNotExist, ValueError):
        return None


def _resolve_assignment_group(ctx, raw) -> AssignmentGroup | None:
    if raw in (None, ""):
        return None
    try:
        return AssignmentGroup.all_objects.get(
            pk=raw, organization=ctx.organization,
        )
    except (AssignmentGroup.DoesNotExist, ValueError):
        return None


def _resolve_program(ctx, raw) -> Program | None:
    if raw in (None, ""):
        return None
    try:
        return Program.all_objects.get(pk=raw, organization=ctx.organization)
    except (Program.DoesNotExist, ValueError):
        return None


def _resolve_person(ctx, raw) -> Person | None:
    if raw in (None, ""):
        return None
    try:
        return Person.all_objects.get(pk=raw, organization=ctx.organization)
    except (Person.DoesNotExist, ValueError):
        return None
