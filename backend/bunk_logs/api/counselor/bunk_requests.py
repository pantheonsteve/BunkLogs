"""Bunk-scoped counselor request list + detail helpers (Stories 7 + 8)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Q

from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import MaintenanceTicket
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Order
from bunk_logs.core.models import OrderActivityEvent
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.state_machine import OrderStateMachine

from .common import person_display_name

if TYPE_CHECKING:
    from bunk_logs.core.models import Organization
    from bunk_logs.core.models import Program

OPEN_STATUSES: tuple[str, ...] = (OrderStateMachine.NEW, OrderStateMachine.IN_PROGRESS)
EDITABLE_ORDER_STATUSES: tuple[str, ...] = (OrderStateMachine.NEW,)
CLOSED_STATUSES: tuple[str, ...] = (
    OrderStateMachine.FULFILLED,
    OrderStateMachine.UNABLE_TO_FULFILL,
)


def counselor_membership_ids_for_bunk(bunk: AssignmentGroup) -> list[int]:
    """Program ``Membership`` ids for active authors on ``bunk``."""
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
            program_id=bunk.program_id,
            is_active=True,
        ).values_list("id", flat=True),
    )


def bunk_camper_ids(bunk: AssignmentGroup) -> set[int]:
    return set(
        AssignmentGroupMembership.objects.filter(
            group=bunk, role_in_group="subject", is_active=True,
        ).values_list("person_id", flat=True),
    )


def _order_matches_bunk(order: Order, bunk: AssignmentGroup, camper_ids: set[int]) -> bool:
    if order.submitted_from_bunk_id == bunk.id:
        return True
    return bool(order.subject_id and order.subject_id in camper_ids)


def viewer_membership_ids(viewer: Person, organization: Organization) -> list[int]:
    """Active program membership ids for ``viewer`` in ``organization``."""
    return list(
        Membership.all_objects.filter(
            person=viewer,
            program__organization=organization,
            is_active=True,
        ).values_list("id", flat=True),
    )


def _bunk_name_for_order(
    order: Order,
    *,
    bunk_by_id: dict[int, AssignmentGroup],
    camper_bunk_by_person: dict[int, int],
) -> tuple[int | None, str | None]:
    if order.submitted_from_bunk_id and order.submitted_from_bunk_id in bunk_by_id:
        bunk = bunk_by_id[order.submitted_from_bunk_id]
        return bunk.id, bunk.name
    if order.subject_id and order.subject_id in camper_bunk_by_person:
        bunk_id = camper_bunk_by_person[order.subject_id]
        bunk = bunk_by_id.get(bunk_id)
        if bunk:
            return bunk.id, bunk.name
    return None, None


def viewer_open_requests(
    *,
    organization: Organization,
    viewer: Person,
    bunks: list[AssignmentGroup],
    include_closed: bool = False,
) -> list[dict]:
    """All open camper-care + maintenance requests the viewer filed (any program)."""
    membership_ids = viewer_membership_ids(viewer, organization)
    if not membership_ids:
        return []

    bunk_by_id = {b.id: b for b in bunks}
    camper_bunk_by_person: dict[int, int] = {}
    for bunk in bunks:
        for camper_id in bunk_camper_ids(bunk):
            camper_bunk_by_person.setdefault(camper_id, bunk.id)

    status_filter = {} if include_closed else {"status__in": OPEN_STATUSES}

    orders = list(
        Order.all_objects.filter(
            organization=organization,
            submitted_by_id__in=membership_ids,
            **status_filter,
        )
        .select_related("subject", "submitted_by__person")
        .order_by("-created_at"),
    )
    tickets = list(
        MaintenanceTicket.all_objects.filter(
            organization=organization,
            submitted_by_id__in=membership_ids,
            **status_filter,
        )
        .select_related("submitted_by__person")
        .order_by("-created_at"),
    )

    rows: list[dict] = []
    for order in orders:
        row = _serialize_order_row(order)
        bunk_id, bunk_name = _bunk_name_for_order(
            order,
            bunk_by_id=bunk_by_id,
            camper_bunk_by_person=camper_bunk_by_person,
        )
        row["bunk_id"] = bunk_id
        row["bunk_name"] = bunk_name
        rows.append(row)
    for ticket in tickets:
        row = _serialize_ticket_row(ticket)
        row["bunk_id"] = None
        row["bunk_name"] = None
        rows.append(row)

    rows.sort(key=lambda r: r["submitted_at"] or "", reverse=True)
    return rows


def bunk_requests_for_viewer(
    *,
    organization: Organization,
    program: Program,
    bunk: AssignmentGroup,
    viewer: Person,
    membership: Membership,
    include_closed: bool = False,
) -> list[dict]:
    """Open camper-care requests the viewer filed for ``bunk`` (maintenance is org-wide)."""
    membership_ids = viewer_membership_ids(viewer, organization)
    if not membership_ids:
        return []

    camper_ids = bunk_camper_ids(bunk)
    status_filter = {} if include_closed else {"status__in": OPEN_STATUSES}

    orders = Order.all_objects.filter(
        organization=organization,
        submitted_by_id__in=membership_ids,
        **status_filter,
    ).select_related("subject", "submitted_by__person")

    order_q = Q(submitted_from_bunk_id=bunk.id)
    if camper_ids:
        order_q |= Q(subject_id__in=camper_ids)
    orders = orders.filter(order_q).order_by("-created_at")

    rows: list[dict] = []
    for order in orders:
        rows.append(_serialize_order_row(order))

    rows.sort(key=lambda r: r["submitted_at"] or "", reverse=True)
    return rows


def viewer_open_request_count(
    *,
    organization: Organization,
    program: Program,
    viewer: Person,
    membership: Membership,
    bunks: list[AssignmentGroup],
) -> int:
    """Count distinct open requests across the viewer's programs."""
    del program, membership  # kept for call-site compatibility
    return len(viewer_open_requests(
        organization=organization,
        viewer=viewer,
        bunks=bunks,
        include_closed=False,
    ))


def _serialize_order_row(order: Order) -> dict:
    subject = order.subject
    subject_name = person_display_name(subject) if subject else None
    return {
        "type": "camper_care",
        "id": str(order.id),
        "status": order.status,
        "status_label": order.get_status_display(),
        "title": order.item or "Camper Care request",
        "subtitle": f"For {subject_name}" if subject_name else "Bunk-wide request",
        "item": order.item or "",
        "item_note": order.item_note or "",
        "subject": (
            {"id": subject.id, "name": subject_name}
            if subject else None
        ),
        "submitted_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
    }


def _serialize_ticket_row(ticket: MaintenanceTicket) -> dict:
    return {
        "type": "maintenance",
        "id": str(ticket.id),
        "status": ticket.status,
        "status_label": ticket.get_status_display(),
        "title": ticket.location or ticket.get_category_display() or "Maintenance request",
        "subtitle": ticket.get_category_display() if ticket.category else "",
        "location": ticket.location or "",
        "category": ticket.category or "",
        "category_label": ticket.get_category_display() if ticket.category else "",
        "urgency": ticket.urgency or "",
        "urgency_label": ticket.get_urgency_display() if ticket.urgency else "",
        "description": ticket.description or "",
        "photo_count": ticket.photos.count() if hasattr(ticket, "photos") else 0,
        "submitted_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
    }


def order_editable_for_viewer(*, order: Order) -> bool:
    """Submitter may edit camper-care fields while the request is still New."""
    return order.status in EDITABLE_ORDER_STATUSES


def order_detail_for_viewer(*, order: Order) -> dict:
    """Read-only camper-care request detail for the submitting counselor."""
    subject = order.subject
    subject_name = person_display_name(subject) if subject else None
    activity = list(
        OrderActivityEvent.objects.filter(
            content_type="order", content_id=order.id,
        )
        .select_related("actor_membership__person")
        .order_by("created_at"),
    )
    return {
        "order": {
            "id": str(order.id),
            "status": order.status,
            "status_label": order.get_status_display(),
            "item": order.item or "",
            "item_note": order.item_note or "",
            "description": order.description or "",
            "subject": (
                {"id": subject.id, "name": subject_name}
                if subject else None
            ),
            "available_transitions": order.available_transitions(),
            "editable": order_editable_for_viewer(order=order),
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        },
        "activity": [_activity_payload(event) for event in activity],
        "scope": "viewer",
    }


def _activity_payload(event: OrderActivityEvent) -> dict:
    actor_person = None
    if event.actor_membership_id and event.actor_membership:
        actor_person = event.actor_membership.person
    return {
        "id": str(event.id),
        "event_type": event.event_type,
        "from_state": event.from_state,
        "to_state": event.to_state,
        "note": event.note,
        "reason": event.reason,
        "actor_name": person_display_name(actor_person) if actor_person else None,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }
