"""Camper Care orders workspace (Stories 22 & 23).

Endpoints:

* ``GET  /api/v1/camper-care/orders/`` — three-section workspace
* ``POST /api/v1/camper-care/orders/<id>/transition/`` — state transition
* ``POST /api/v1/camper-care/orders/bulk-transition/`` — bulk fulfillment

The transition endpoints delegate to the shared state-machine views
from Step 7_2 so the correction window + activity log behave identically
to the generic ``/api/v1/orders/...`` paths. The role-namespaced URLs
exist mostly so the frontend can route consistently under the camper-
care surface; both routes hit the same underlying logic.

Per CC7 (Story 22 decision 5), the workspace is **program-scoped** --
all Camper Care members in a program see the same queue, *not* a
caseload subset. The optional ``filter=my_caseload`` flag narrows to
the viewer's caseload for the My-Caseload filter chip (Story 22
criterion 6).
"""

from __future__ import annotations

from django.utils.dateparse import parse_date
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.api.orders_state_machine import OrderBulkTransitionView
from bunk_logs.api.orders_state_machine import OrderTransitionView
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Order
from bunk_logs.core.models import OrderActivityEvent

from .common import bunk_camper_ids
from .common import caseload_bunks
from .common import caseload_camper_ids
from .common import orders_base_queryset
from .common import resolve_orders_viewer

ACTIVE_STATUSES: tuple[str, ...] = (Order.Status.NEW, Order.Status.IN_PROGRESS)
CLOSED_STATUSES: tuple[str, ...] = (Order.Status.FULFILLED, Order.Status.UNABLE_TO_FULFILL)
FILTER_CHOICES: frozenset[str] = frozenset({"all", "my_caseload", "by_bunk", "by_item"})


class CamperCareOrdersListView(APIView):
    """``GET /api/v1/camper-care/orders/`` — three-section workspace.

    Query params:

    * ``filter`` — ``all`` (default), ``my_caseload``, ``by_bunk``, ``by_item``
    * ``bunk_id`` — required when ``filter=by_bunk``
    * ``item`` — required when ``filter=by_item`` (exact label match)
    * ``resolved_since`` / ``resolved_until`` — clamp Resolved section
      (Story 22 criterion 7)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = resolve_orders_viewer(request)
        filt = (request.query_params.get("filter") or "all").lower()
        if filt not in FILTER_CHOICES:
            msg = f"Unknown filter {filt!r}."
            raise ValidationError({"filter": msg})
        if ctx.scope != "team" and filt != "all":
            raise ValidationError(
                {"filter": "Only the 'all' filter is available for your role."},
            )

        qs = orders_base_queryset(ctx).select_related(
            "subject", "submitted_by__person", "submitted_from_bunk",
        )
        if filt == "my_caseload":
            camper_ids = caseload_camper_ids(ctx.membership)
            qs = qs.filter(subject_id__in=camper_ids)
        elif filt == "by_bunk":
            bunk_id = request.query_params.get("bunk_id")
            if not bunk_id:
                raise ValidationError({"bunk_id": "Required when filter=by_bunk."})
            try:
                bunk_pk = int(bunk_id)
            except ValueError as e:
                raise ValidationError({"bunk_id": "Must be an integer."}) from e
            allowed_bunk_ids = _allowed_bunk_ids(ctx)
            if bunk_pk not in allowed_bunk_ids:
                raise ValidationError(
                    {"bunk_id": "Bunk is outside your orders scope."},
                )
            from bunk_logs.core.models import AssignmentGroup
            bunk = AssignmentGroup.all_objects.filter(pk=bunk_pk).first()
            if bunk is None:
                raise ValidationError({"bunk_id": "Unknown bunk."})
            qs = qs.filter(subject_id__in=bunk_camper_ids(bunk))
        elif filt == "by_item":
            item = (request.query_params.get("item") or "").strip()
            if not item:
                raise ValidationError({"item": "Required when filter=by_item."})
            qs = qs.filter(item=item)

        resolved_since = _parse_optional_date(request.query_params.get("resolved_since"))
        resolved_until = _parse_optional_date(request.query_params.get("resolved_until"))

        rows = list(qs.order_by("-created_at"))
        org_wide = ctx.scope == "team" and ctx.membership.role == "admin"
        subject_ids = {o.subject_id for o in rows if o.subject_id}
        submitter_person_ids = {
            o.submitted_by.person_id
            for o in rows
            if o.submitted_by_id and o.submitted_by.person_id
        }
        if org_wide:
            bunk_by_subject = _bunk_by_subject_ids_org(
                subject_ids=subject_ids,
                organization_id=ctx.organization.id,
            )
            bunk_by_submitter = _bunk_by_author_person_ids_org(
                person_ids=submitter_person_ids,
                organization_id=ctx.organization.id,
            )
        else:
            bunk_by_subject = _bunk_by_subject_ids(
                subject_ids=subject_ids,
                program_id=ctx.program.id,
            )
            bunk_by_submitter = _bunk_by_author_person_ids(
                person_ids=submitter_person_ids,
                program_id=ctx.program.id,
            )
        new_items: list[dict] = []
        in_progress: list[dict] = []
        resolved: list[dict] = []
        for o in rows:
            payload = _order_payload(
                o,
                bunk_by_subject=bunk_by_subject,
                bunk_by_submitter=bunk_by_submitter,
                scope=ctx.scope,
            )
            if o.status == Order.Status.NEW:
                new_items.append(payload)
            elif o.status == Order.Status.IN_PROGRESS:
                in_progress.append(payload)
            else:
                # Closed section: optional date clamp
                if resolved_since and o.updated_at.date() < resolved_since:
                    continue
                if resolved_until and o.updated_at.date() > resolved_until:
                    continue
                resolved.append(payload)

        return Response({
            "new": new_items,
            "in_progress": in_progress,
            "resolved": resolved,
            "counts": {
                "new": len(new_items),
                "in_progress": len(in_progress),
                "resolved": len(resolved),
            },
            "scope": ctx.scope,
        })


class CamperCareOrderTransitionView(OrderTransitionView):
    """Role-namespaced alias for ``/api/v1/orders/<id>/transition/``.

    Inheriting the shared view keeps the contract (permission gate,
    correction window, activity payload) identical; we only override
    the URL kwarg name so the route can stay role-readable.
    """

    def post(self, request, order_id, *args, **kwargs):
        return super().post(request, order_id, *args, **kwargs)


class CamperCareOrderBulkTransitionView(OrderBulkTransitionView):
    """Role-namespaced alias for ``/api/v1/orders/bulk-transition/`` (Story 23.5)."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _allowed_bunk_ids(ctx) -> set[int]:
    """Bunk IDs the viewer may use with ``filter=by_bunk``."""
    if ctx.scope == "team" and ctx.membership.role == "admin":
        from bunk_logs.core.models import AssignmentGroup
        return set(
            AssignmentGroup.all_objects.filter(
                organization=ctx.organization,
                group_type="bunk",
                is_active=True,
            ).values_list("id", flat=True),
        )
    if ctx.scope == "team":
        return {b.id for b in caseload_bunks(ctx.membership)}
    if ctx.scope == "unit":
        from bunk_logs.api.unit_head.common import supervised_bunk_ids
        return supervised_bunk_ids(ctx.membership, today=ctx.today)
    from bunk_logs.api.counselor.common import viewer_bunk_groups
    return {b.id for b in viewer_bunk_groups(ctx.person)}


def _parse_optional_date(raw: str | None):
    if not raw:
        return None
    parsed = parse_date(raw)
    if parsed is None:
        msg = f"Invalid date {raw!r}; expected YYYY-MM-DD."
        raise ValidationError(msg)
    return parsed


def _bunk_by_subject_ids(*, subject_ids: set[int], program_id: int) -> dict[int, dict]:
    """Active bunk membership per camper in ``program_id`` (first match wins)."""
    return _bunk_lookup(
        person_ids=subject_ids,
        program_id=program_id,
        role_in_group="subject",
    )


def _bunk_by_subject_ids_org(*, subject_ids: set[int], organization_id: int) -> dict[int, dict]:
    return _bunk_lookup_org(
        person_ids=subject_ids,
        organization_id=organization_id,
        role_in_group="subject",
    )


def _bunk_by_author_person_ids(*, person_ids: set[int], program_id: int) -> dict[int, dict]:
    """Active author bunk per counselor Person in ``program_id``."""
    return _bunk_lookup(
        person_ids=person_ids,
        program_id=program_id,
        role_in_group="author",
    )


def _bunk_by_author_person_ids_org(*, person_ids: set[int], organization_id: int) -> dict[int, dict]:
    return _bunk_lookup_org(
        person_ids=person_ids,
        organization_id=organization_id,
        role_in_group="author",
    )


def _bunk_lookup(
    *,
    person_ids: set[int],
    program_id: int,
    role_in_group: str,
) -> dict[int, dict]:
    if not person_ids:
        return {}
    rows = AssignmentGroupMembership.objects.filter(
        person_id__in=person_ids,
        role_in_group=role_in_group,
        is_active=True,
        group__group_type="bunk",
        group__is_active=True,
        group__program_id=program_id,
    ).values("person_id", "group_id", "group__name")
    out: dict[int, dict] = {}
    for row in rows:
        person_id = row["person_id"]
        if person_id in out:
            continue
        out[person_id] = {
            "id": row["group_id"],
            "name": row["group__name"] or "",
        }
    return out


def _bunk_lookup_org(
    *,
    person_ids: set[int],
    organization_id: int,
    role_in_group: str,
) -> dict[int, dict]:
    if not person_ids:
        return {}
    rows = AssignmentGroupMembership.objects.filter(
        person_id__in=person_ids,
        role_in_group=role_in_group,
        is_active=True,
        group__group_type="bunk",
        group__is_active=True,
        group__organization_id=organization_id,
    ).values("person_id", "group_id", "group__name")
    out: dict[int, dict] = {}
    for row in rows:
        person_id = row["person_id"]
        if person_id in out:
            continue
        out[person_id] = {
            "id": row["group_id"],
            "name": row["group__name"] or "",
        }
    return out


def _resolve_order_bunk(
    order: Order,
    *,
    bunk_by_subject: dict[int, dict] | None,
    bunk_by_submitter: dict[int, dict] | None,
) -> dict | None:
    if order.submitted_from_bunk_id and order.submitted_from_bunk:
        return {
            "id": order.submitted_from_bunk_id,
            "name": order.submitted_from_bunk.name or "",
        }
    if (
        bunk_by_submitter
        and order.submitted_by_id
        and order.submitted_by.person_id
    ):
        bunk = bunk_by_submitter.get(order.submitted_by.person_id)
        if bunk:
            return bunk
    if bunk_by_subject and order.subject_id:
        return bunk_by_subject.get(order.subject_id)
    return None


def _order_payload(
    order: Order,
    *,
    bunk_by_subject: dict[int, dict] | None = None,
    bunk_by_submitter: dict[int, dict] | None = None,
    scope: str = "team",
) -> dict:
    submitter = order.submitted_by
    submitter_person = getattr(submitter, "person", None) if submitter else None
    age_seconds = None
    if order.created_at is not None:
        from django.utils import timezone
        age_seconds = int((timezone.now() - order.created_at).total_seconds())
    last_event = (
        OrderActivityEvent.objects.filter(
            content_type="order", content_id=order.id,
        ).order_by("-created_at").first()
    )
    bunk = _resolve_order_bunk(
        order,
        bunk_by_subject=bunk_by_subject,
        bunk_by_submitter=bunk_by_submitter,
    )
    return {
        "id": str(order.id),
        "status": order.status,
        "available_transitions": (
            order.available_transitions() if scope == "team" else []
        ),
        "is_within_correction_window": (
            order.can_correct_last_transition() if scope == "team" else False
        ),
        "subject": _camper_brief(order.subject),
        "bunk": bunk,
        "item": order.item,
        "item_note": order.item_note,
        "description": order.description,
        "submitter": {
            "membership_id": submitter.id if submitter else None,
            "role": submitter.role if submitter else None,
            "name": (
                f"{submitter_person.first_name} {submitter_person.last_name}".strip()
                if submitter_person else None
            ),
        },
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        "age_seconds": age_seconds,
        "last_event_note": (last_event.note if last_event else ""),
    }


def _camper_brief(camper) -> dict | None:
    if camper is None:
        return None
    return {
        "id": camper.id,
        "first_name": camper.first_name,
        "last_name": camper.last_name,
        "preferred_name": camper.preferred_name,
    }
