"""HTTP layer for the shared order/ticket state machine (Step 7_2).

These views deliberately live in their own module instead of being grafted
onto the legacy ``orders`` ViewSet (which still serves Crane Lake's old
order data model). Routing keeps the legacy paths intact by typing the
new lookups as ``<uuid:order_id>``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction
from rest_framework import permissions
from rest_framework import status as http_status
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.models import MaintenanceTicket
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Order
from bunk_logs.core.models import OrderActivityEvent
from bunk_logs.core.models import Person
from bunk_logs.core.permissions import is_super_admin
from bunk_logs.core.state_machine import CorrectionWindowExpiredError
from bunk_logs.core.state_machine import InvalidTransitionError
from bunk_logs.core.state_machine import MissingReasonError
from bunk_logs.core.state_machine import NoTransitionToCorrectError
from bunk_logs.core.state_machine import OrderStateMachine
from bunk_logs.core.state_machine import OrderStateMachineError

if TYPE_CHECKING:
    from collections.abc import Iterable


def _person_for_request(request) -> Person | None:
    if not request.user.is_authenticated or not getattr(request, "organization", None):
        return None
    return Person.all_objects.filter(user=request.user).first()


def _actor_membership_for(request, *, content) -> Membership | None:
    """Return the actor's Membership in the program of ``content`` (if any).

    Falls through to ``None`` for super-admins so the view can still pass
    a ``None`` actor; callers that require a Membership should reject ``None``.
    """
    person = _person_for_request(request)
    if person is None:
        return None
    return (
        Membership.objects.filter(
            person=person,
            program=content.program,
            is_active=True,
        )
        .order_by("-created_at")
        .first()
    )


def _can_transition(request, *, content, fulfilling_role: str) -> bool:
    """Whether ``request.user`` is allowed to transition ``content``.

    Allowed when the user is a Super Admin, an org Admin, or an active
    Membership in the program with the fulfilling role for this content type.
    """
    if is_super_admin(request.user):
        return True
    person = _person_for_request(request)
    if person is None:
        return False
    return Membership.objects.filter(
        person=person,
        program=content.program,
        is_active=True,
        role__in=("admin", fulfilling_role),
    ).exists()


def _activity_payload(events: Iterable[OrderActivityEvent]) -> list[dict]:
    return [
        {
            "id": str(e.id),
            "event_type": e.event_type,
            "from_state": e.from_state,
            "to_state": e.to_state,
            "note": e.note,
            "reason": e.reason,
            "actor_membership_id": e.actor_membership_id,
            "actor_name": (
                e.actor_membership.person.full_name
                if e.actor_membership and e.actor_membership.person
                else None
            ),
            "correction_of": str(e.correction_of_id) if e.correction_of_id else None,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]


def _content_payload(content) -> dict:
    out = {
        "id": str(content.id),
        "status": content.status,
        "urgency": content.urgency,
        "available_transitions": content.available_transitions(),
        "last_transition_at": (
            content.last_transition_at.isoformat()
            if content.last_transition_at
            else None
        ),
        "is_within_correction_window": content.can_correct_last_transition(),
    }
    if isinstance(content, MaintenanceTicket):
        out["title"] = content.title
        out["description"] = content.description
        out["urgent_reason"] = content.urgent_reason
    elif isinstance(content, Order):
        out["description"] = content.description
        out["subject_id"] = content.subject_id
    return out


def _activity_for(content) -> list[OrderActivityEvent]:
    label = content._content_type_label()
    return list(
        OrderActivityEvent.objects.filter(
            content_type=label, content_id=content.id,
        )
        .select_related("actor_membership__person")
        .order_by("created_at"),
    )


def _machine_error_response(exc: OrderStateMachineError) -> Response:
    code = http_status.HTTP_400_BAD_REQUEST
    detail = str(exc)
    if isinstance(exc, MissingReasonError):
        return Response({"reason": detail}, status=code)
    if isinstance(exc, InvalidTransitionError):
        return Response({"to_state": detail}, status=code)
    if isinstance(exc, CorrectionWindowExpiredError):
        return Response({"detail": detail}, status=http_status.HTTP_409_CONFLICT)
    if isinstance(exc, NoTransitionToCorrectError):
        return Response({"detail": detail}, status=http_status.HTTP_409_CONFLICT)
    return Response({"detail": detail}, status=code)


class _OrderableBaseView(APIView):
    """Shared infrastructure for transition / correction endpoints."""

    permission_classes = [permissions.IsAuthenticated]
    model = None  # subclasses set Order or MaintenanceTicket
    fulfilling_role = ""  # subclasses set "camper_care" or "maintenance"

    def _get_object(self, request, content_id):
        if not getattr(request, "organization", None):
            return None, Response(
                {"detail": "Organization context required."},
                status=http_status.HTTP_403_FORBIDDEN,
            )
        instance = self.model.objects.filter(pk=content_id).first()
        if instance is None:
            return None, Response(
                {"detail": "Not found."}, status=http_status.HTTP_404_NOT_FOUND,
            )
        if not _can_transition(
            request, content=instance, fulfilling_role=self.fulfilling_role,
        ):
            return None, Response(
                {"detail": "You do not have permission to transition this item."},
                status=http_status.HTTP_403_FORBIDDEN,
            )
        return instance, None


class OrderTransitionView(_OrderableBaseView):
    model = Order
    fulfilling_role = "camper_care"

    def post(self, request, order_id):
        instance, error = self._get_object(request, order_id)
        if error is not None:
            return error
        return _do_transition(
            request, instance, fulfilling_role=self.fulfilling_role,
        )


class OrderBulkTransitionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        return _do_bulk_transition(
            request, model=Order, fulfilling_role="camper_care",
        )


class OrderCorrectLastView(_OrderableBaseView):
    model = Order
    fulfilling_role = "camper_care"

    def post(self, request, order_id):
        instance, error = self._get_object(request, order_id)
        if error is not None:
            return error
        return _do_correct(
            request, instance, fulfilling_role=self.fulfilling_role,
        )


class MaintenanceTicketTransitionView(_OrderableBaseView):
    model = MaintenanceTicket
    fulfilling_role = "maintenance"

    def post(self, request, ticket_id):
        instance, error = self._get_object(request, ticket_id)
        if error is not None:
            return error
        return _do_transition(
            request, instance, fulfilling_role=self.fulfilling_role,
        )


class MaintenanceTicketBulkTransitionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        return _do_bulk_transition(
            request, model=MaintenanceTicket, fulfilling_role="maintenance",
        )


class MaintenanceTicketCorrectLastView(_OrderableBaseView):
    model = MaintenanceTicket
    fulfilling_role = "maintenance"

    def post(self, request, ticket_id):
        instance, error = self._get_object(request, ticket_id)
        if error is not None:
            return error
        return _do_correct(
            request, instance, fulfilling_role=self.fulfilling_role,
        )


def _do_transition(request, instance, *, fulfilling_role: str) -> Response:
    to_state = (request.data.get("to_state") or "").strip()
    note = request.data.get("note") or ""
    reason = request.data.get("reason") or ""
    if not to_state:
        return Response(
            {"to_state": "This field is required."},
            status=http_status.HTTP_400_BAD_REQUEST,
        )
    if not OrderStateMachine.is_valid_state(to_state):
        return Response(
            {"to_state": f"Unknown state {to_state!r}."},
            status=http_status.HTTP_400_BAD_REQUEST,
        )

    actor = _actor_membership_for(request, content=instance)
    if actor is None and not is_super_admin(request.user):
        return Response(
            {"detail": "No active Membership in this Program."},
            status=http_status.HTTP_403_FORBIDDEN,
        )

    try:
        instance.transition_to(to_state, actor=actor, note=note, reason=reason)
    except OrderStateMachineError as exc:
        return _machine_error_response(exc)

    return Response(
        {
            "content": _content_payload(instance),
            "activity": _activity_payload(_activity_for(instance)),
        },
        status=http_status.HTTP_200_OK,
    )


def _do_correct(request, instance, *, fulfilling_role: str) -> Response:
    actor = _actor_membership_for(request, content=instance)
    if actor is None and not is_super_admin(request.user):
        return Response(
            {"detail": "No active Membership in this Program."},
            status=http_status.HTTP_403_FORBIDDEN,
        )
    try:
        instance.correct_last_transition(actor=actor)
    except OrderStateMachineError as exc:
        return _machine_error_response(exc)
    return Response(
        {
            "content": _content_payload(instance),
            "activity": _activity_payload(_activity_for(instance)),
        },
        status=http_status.HTTP_200_OK,
    )


def _do_bulk_transition(request, *, model, fulfilling_role: str) -> Response:
    if not getattr(request, "organization", None):
        return Response(
            {"detail": "Organization context required."},
            status=http_status.HTTP_403_FORBIDDEN,
        )
    ids = request.data.get("ids") or []
    if not isinstance(ids, list) or not ids:
        return Response(
            {"ids": "Provide a non-empty list of UUIDs."},
            status=http_status.HTTP_400_BAD_REQUEST,
        )
    to_state = (request.data.get("to_state") or "").strip()
    if not OrderStateMachine.is_valid_state(to_state):
        return Response(
            {"to_state": f"Unknown state {to_state!r}."},
            status=http_status.HTTP_400_BAD_REQUEST,
        )
    note = request.data.get("note") or ""
    reason = request.data.get("reason") or ""

    instances = list(model.objects.filter(pk__in=ids))
    found_ids = {str(i.id) for i in instances}
    missing = [i for i in ids if i not in found_ids]

    failed: list[dict] = []
    transitioned: list[dict] = []
    activity_by_id: dict[str, list[dict]] = {}
    for instance in instances:
        if not _can_transition(
            request, content=instance, fulfilling_role=fulfilling_role,
        ):
            failed.append(
                {"id": str(instance.id), "error": "permission_denied"},
            )
            continue
        actor = _actor_membership_for(request, content=instance)
        if actor is None and not is_super_admin(request.user):
            failed.append(
                {"id": str(instance.id), "error": "no_membership"},
            )
            continue
        try:
            with transaction.atomic():
                instance.transition_to(
                    to_state, actor=actor, note=note, reason=reason,
                )
        except OrderStateMachineError as exc:
            failed.append({"id": str(instance.id), "error": str(exc)})
            continue
        transitioned.append(_content_payload(instance))
        activity_by_id[str(instance.id)] = _activity_payload(
            _activity_for(instance),
        )

    payload = {
        "transitioned": transitioned,
        "activity_by_id": activity_by_id,
        "failed": failed,
        "missing": missing,
    }
    code = (
        http_status.HTTP_207_MULTI_STATUS
        if (failed or missing)
        else http_status.HTTP_200_OK
    )
    return Response(payload, status=code)
