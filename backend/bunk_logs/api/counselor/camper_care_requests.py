"""``POST /api/v1/counselor/camper-care-requests/`` — Story 7.

Counselor-side submission for a Camper Care request. Idempotent on
``(program, client_submission_id)`` so the offline queue can retry.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core import audit as audit_module
from bunk_logs.core.catalog import camper_care_item_options
from bunk_logs.core.catalog import resolve_line_items
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Order
from bunk_logs.core.models import RequestLineItem
from bunk_logs.core.program_scope import primary_operational_membership
from bunk_logs.core.submission import idempotent_create

from .common import co_counselor_person_ids
from .common import invalidate_dashboard_for_viewers
from .common import resolve_submitted_from_bunk
from .common import viewer_bunk_groups
from .common import viewer_or_403
from .responses import order_response
from .serializers import CamperCareRequestCreateSerializer


class CamperCareItemSuggestionListView(APIView):
    """``GET /api/v1/counselor/camper-care-item-suggestions/`` — Story 7 criterion 2.ii.

    Returns the curated camper-care item list for the viewer's primary
    program (decision C6). The form uses this for autocomplete; counselors
    can still submit any free-text label, so an empty list (e.g. for a
    program that hasn't been seeded yet) just disables autocomplete on
    the client without blocking submission.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        viewer = ctx.person

        primary_membership = primary_operational_membership(viewer, today=ctx.today)
        if primary_membership is None or primary_membership.program is None:
            return Response({"suggestions": []})

        program = primary_membership.program
        # Catalog-backed (Step 7_catalog): the curated list now lives in
        # CatalogItem under the Camper Care store. Counselors can still submit
        # any free-text label, so an empty list just disables autocomplete.
        suggestions = camper_care_item_options(ctx.organization, program)
        return Response({"suggestions": suggestions})


class CamperCareRequestCreateView(APIView):
    """Counselor POST for a Camper Care request."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["post", "head", "options"]

    def post(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        viewer, org, today = ctx.person, ctx.organization, ctx.today

        serializer = CamperCareRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        primary_membership = primary_operational_membership(viewer, today=today)
        if primary_membership is None or primary_membership.program is None:
            msg = "No active program membership."
            raise PermissionDenied(msg)
        program = primary_membership.program

        # Subject is optional but if supplied must be a camper on one of
        # the viewer's bunks (Story 7 criterion 2.i). Bunk-scoped requests
        # without a subject are allowed for "the bunk in general" needs.
        subject_id = payload.get("subject_id")
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

        submitted_from_bunk = resolve_submitted_from_bunk(
            viewer=viewer,
            subject_id=subject_id,
            bunk_id=payload.get("bunk_id"),
        )

        # Resolve line items (catalog or free-text) up front so an invalid
        # item id fails before we create the Order.
        resolved_lines = resolve_line_items(
            org,
            program,
            "camper_care",
            payload.get("line_items"),
            legacy_item=payload.get("item", ""),
            legacy_note=payload.get("item_note", ""),
        )
        # Order.item keeps a summary of the first line for back-compat with
        # surfaces that still read the scalar field.
        summary_label = resolved_lines[0]["item_label"] if resolved_lines else payload.get("item", "")

        def _create_order():
            order = Order(
                organization=org,
                program=program,
                subject_id=subject_id,
                submitted_by=primary_membership,
                submitted_from_bunk=submitted_from_bunk,
                item=summary_label,
                item_note=payload.get("item_note", ""),
                description=payload.get("description", ""),
                client_submission_id=payload["client_submission_id"],
            )
            order.full_clean()
            order.save()
            for line in resolved_lines:
                RequestLineItem.objects.create(
                    organization=org,
                    order=order,
                    item=line["item"],
                    item_label=line["item_label"],
                    quantity=line["quantity"],
                    note=line["note"],
                )
            return order

        try:
            order, created = idempotent_create(
                Order,
                program=program,
                client_submission_id=payload["client_submission_id"],
                create_fn=_create_order,
            )
        except DjangoValidationError as e:
            return Response(
                e.message_dict if hasattr(e, "message_dict") else str(e),
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not created:
            return Response(order_response(order), status=status.HTTP_200_OK)

        audit_module.created(
            primary_membership,
            order,
            after_state={
                "item": order.item,
                "item_note": order.item_note,
                "description": order.description,
                "status": order.status,
                "subject_id": order.subject_id,
            },
            content_type="order",
        )

        # Bust caches for viewer + all co-counselors so the dashboard's
        # requests section reflects the new row within seconds.
        bunks = viewer_bunk_groups(viewer)
        co_ids = co_counselor_person_ids(viewer, bunks)
        invalidate_dashboard_for_viewers(org, co_ids | {viewer.id}, today)

        return Response(order_response(order), status=status.HTTP_201_CREATED)
