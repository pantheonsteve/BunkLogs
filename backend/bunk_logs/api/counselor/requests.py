"""Counselor request list and camper-care detail/update endpoints.

``GET /api/v1/counselor/requests/`` returns the viewer's submitted requests.
``GET/PATCH /api/v1/counselor/requests/camper-care/<id>/`` loads or edits an
open camper-care request the viewer filed (PATCH allowed while status is New).
"""

from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core import audit as audit_module
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import MaintenanceTicket
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Order
from bunk_logs.core.program_scope import primary_operational_membership
from bunk_logs.core.state_machine import OrderStateMachine

from .bunk_requests import order_detail_for_viewer
from .bunk_requests import order_editable_for_viewer
from .bunk_requests import viewer_membership_ids
from .common import invalidate_dashboard_for_viewers
from .common import person_display_name
from .common import resolve_submitted_from_bunk
from .common import viewer_bunk_groups
from .common import viewer_or_403
from .serializers import CamperCareRequestUpdateSerializer

OPEN_STATUSES: tuple[str, ...] = (OrderStateMachine.NEW, OrderStateMachine.IN_PROGRESS)


class CounselorRequestsListView(APIView):
    """Combined camper-care + maintenance request list."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        viewer = ctx.person
        org = ctx.organization

        primary_membership = primary_operational_membership(viewer, today=ctx.today)
        if primary_membership is None or primary_membership.program is None:
            return Response({"requests": []})
        program = primary_membership.program

        membership_id_to_person_id: dict[int, int] = dict(
            Membership.all_objects.filter(
                person=viewer,
                program=program,
            ).values_list("id", "person_id"),
        )
        if not membership_id_to_person_id:
            return Response({"requests": []})

        status_filter = (request.query_params.get("status") or "open").lower()
        if status_filter == "all":
            status_kwargs: dict = {}
        else:
            status_kwargs = {"status__in": OPEN_STATUSES}

        eligible_membership_ids = list(membership_id_to_person_id.keys())

        order_rows = list(
            Order.all_objects.filter(
                organization=org,
                program=program,
                submitted_by_id__in=eligible_membership_ids,
                **status_kwargs,
            )
            .select_related("subject", "submitted_by", "submitted_by__person")
            .order_by("-created_at"),
        )
        ticket_rows = list(
            MaintenanceTicket.all_objects.filter(
                organization=org,
                program=program,
                submitted_by_id__in=eligible_membership_ids,
                **status_kwargs,
            )
            .select_related("submitted_by", "submitted_by__person")
            .order_by("-created_at"),
        )

        results: list[dict] = []
        for o in order_rows:
            submitter_person = o.submitted_by.person if o.submitted_by else None
            is_self = submitter_person == viewer if submitter_person else False
            results.append({
                "type": "camper_care",
                "id": str(o.id),
                "status": o.status,
                "status_label": o.get_status_display(),
                "subject": (
                    {
                        "id": o.subject.id,
                        "name": person_display_name(o.subject),
                    }
                    if o.subject
                    else None
                ),
                "item": o.item or "",
                "item_note": o.item_note or "",
                "submitter": {
                    "is_self": is_self,
                    "name": person_display_name(submitter_person) if not is_self else None,
                },
                "submitted_at": o.created_at.isoformat() if o.created_at else None,
                "updated_at": o.updated_at.isoformat() if o.updated_at else None,
            })
        for t in ticket_rows:
            submitter_person = t.submitted_by.person if t.submitted_by else None
            is_self = submitter_person == viewer if submitter_person else False
            results.append({
                "type": "maintenance",
                "id": str(t.id),
                "status": t.status,
                "status_label": t.get_status_display(),
                "location": t.location or "",
                "category": t.category or "",
                "category_label": t.get_category_display() if t.category else "",
                "urgency": t.urgency or "",
                "urgency_label": t.get_urgency_display() if t.urgency else "",
                "description": t.description or "",
                "photo_count": t.photos.count(),
                "submitter": {
                    "is_self": is_self,
                    "name": person_display_name(submitter_person) if not is_self else None,
                },
                "submitted_at": t.created_at.isoformat() if t.created_at else None,
                "updated_at": t.updated_at.isoformat() if t.updated_at else None,
            })

        # Newest first across the combined list.
        results.sort(key=lambda r: r["submitted_at"] or "", reverse=True)
        return Response({"requests": results})


class CamperCareRequestDetailView(APIView):
    """``GET/PATCH /api/v1/counselor/requests/camper-care/<id>/``."""

    permission_classes = [IsAuthenticated]

    def _order_for_viewer(self, request, order_id):
        ctx = viewer_or_403(request)
        membership_ids = viewer_membership_ids(ctx.person, ctx.organization)
        if not membership_ids:
            msg = "Request not found."
            raise NotFound(msg)
        order = (
            Order.all_objects.filter(
                pk=order_id,
                organization=ctx.organization,
                submitted_by_id__in=membership_ids,
            )
            .select_related("subject")
            .first()
        )
        if order is None:
            msg = "Request not found."
            raise NotFound(msg)
        return ctx, order

    def get(self, request, order_id, *args, **kwargs):
        _, order = self._order_for_viewer(request, order_id)
        return Response(order_detail_for_viewer(order=order))

    def patch(self, request, order_id, *args, **kwargs):
        ctx, order = self._order_for_viewer(request, order_id)
        if not order_editable_for_viewer(order=order):
            msg = "This request can no longer be edited."
            raise PermissionDenied(msg)

        serializer = CamperCareRequestUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        viewer = ctx.person

        before = {
            "item": order.item,
            "item_note": order.item_note,
            "description": order.description,
            "subject_id": order.subject_id,
        }

        if "subject_id" in payload:
            subject_id = payload["subject_id"]
            if subject_id is not None:
                bunks = viewer_bunk_groups(viewer)
                allowed_camper_ids = set(
                    AssignmentGroupMembership.all_objects.filter(
                        group__in=bunks, role_in_group="subject", is_active=True,
                    ).values_list("person_id", flat=True),
                )
                if subject_id not in allowed_camper_ids:
                    raise PermissionDenied(
                        {"subject_id": "Camper is not on any of your bunks."},
                    )
            order.subject_id = subject_id

        if "item" in payload:
            order.item = payload["item"]
        if "item_note" in payload:
            order.item_note = payload["item_note"]
        if "description" in payload:
            order.description = payload["description"]

        if "subject_id" in payload or "bunk_id" in payload:
            order.submitted_from_bunk = resolve_submitted_from_bunk(
                viewer=viewer,
                subject_id=order.subject_id,
                bunk_id=payload.get("bunk_id"),
            )

        try:
            order.full_clean()
            order.save()
        except DjangoValidationError as e:
            return Response(
                e.message_dict if hasattr(e, "message_dict") else str(e),
                status=status.HTTP_400_BAD_REQUEST,
            )

        audit_module.edited(
            order.submitted_by,
            order,
            before,
            {
                "item": order.item,
                "item_note": order.item_note,
                "description": order.description,
                "subject_id": order.subject_id,
            },
            content_type="order",
        )

        invalidate_dashboard_for_viewers(ctx.organization, {viewer.id}, ctx.today)

        return Response(order_detail_for_viewer(order=order))
