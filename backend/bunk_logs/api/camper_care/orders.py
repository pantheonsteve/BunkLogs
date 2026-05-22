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
from bunk_logs.core.models import Order
from bunk_logs.core.models import OrderActivityEvent

from .common import bunk_camper_ids
from .common import caseload_bunks
from .common import caseload_camper_ids
from .common import viewer_or_403

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
        ctx = viewer_or_403(request)
        filt = (request.query_params.get("filter") or "all").lower()
        if filt not in FILTER_CHOICES:
            msg = f"Unknown filter {filt!r}."
            raise ValidationError({"filter": msg})

        qs = Order.objects.filter(program=ctx.program).select_related(
            "subject", "submitted_by__person",
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
            owned = {b.id for b in caseload_bunks(ctx.membership)}
            if bunk_pk not in owned:
                raise ValidationError(
                    {"bunk_id": "Bunk is not on your caseload."},
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
        new_items: list[dict] = []
        in_progress: list[dict] = []
        resolved: list[dict] = []
        for o in rows:
            payload = _order_payload(o)
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


def _parse_optional_date(raw: str | None):
    if not raw:
        return None
    parsed = parse_date(raw)
    if parsed is None:
        msg = f"Invalid date {raw!r}; expected YYYY-MM-DD."
        raise ValidationError(msg)
    return parsed


def _order_payload(order: Order) -> dict:
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
    return {
        "id": str(order.id),
        "status": order.status,
        "available_transitions": order.available_transitions(),
        "is_within_correction_window": order.can_correct_last_transition(),
        "subject": _camper_brief(order.subject),
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
