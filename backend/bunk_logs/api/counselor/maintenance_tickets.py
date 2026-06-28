"""Counselor maintenance ticket write endpoints (Story 8).

- ``POST /api/v1/counselor/maintenance-tickets/`` — create a ticket, optionally
  with photos attached via multipart ``photos`` fields.
- ``POST /api/v1/counselor/maintenance-tickets/<uuid>/photos/`` — add follow-up
  photos to a ticket the viewer submitted (decision C5).

Photos are stored via the configured ``DEFAULT_FILE_STORAGE`` backend: S3 in
production (with presigned URLs) and the local filesystem in dev / tests.
"""

from __future__ import annotations

import json

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser
from rest_framework.parsers import JSONParser
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.api.maintenance.notifications import send_ticket_created_email
from bunk_logs.core import audit as audit_module
from bunk_logs.core.catalog import active_items_for_role
from bunk_logs.core.catalog import maintenance_options
from bunk_logs.core.catalog import resolve_line_items
from bunk_logs.core.models import MaintenanceTicket
from bunk_logs.core.models import Membership
from bunk_logs.core.models import RequestLineItem
from bunk_logs.core.models import TicketPhoto
from bunk_logs.core.program_scope import primary_operational_membership
from bunk_logs.core.submission import idempotent_create

from .common import co_counselor_person_ids
from .common import invalidate_dashboard_for_viewers
from .common import viewer_bunk_groups
from .common import viewer_or_403
from .responses import maintenance_ticket_response
from .responses import ticket_photo_response
from .serializers import MaintenanceTicketCreateSerializer
from .serializers import MaintenanceTicketPhotoUploadSerializer


def _ticket_after_state(ticket: MaintenanceTicket) -> dict:
    return {
        "location": ticket.location,
        "category": ticket.category,
        "description": ticket.description,
        "urgency": ticket.urgency,
        "urgent_reason": ticket.urgent_reason,
        "status": ticket.status,
    }


class MaintenanceOptionsListView(APIView):
    """``GET /api/v1/counselor/maintenance-options/``.

    Returns the configurable Maintenance-store catalog (request types + items)
    for the viewer's program so the ticket form can render category/item
    pickers from the DB instead of hard-coded constants. An empty payload
    means no catalog is configured; the client should fall back to free text.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        primary_membership = primary_operational_membership(ctx.person, today=ctx.today)
        program = primary_membership.program if primary_membership else None
        return Response(maintenance_options(ctx.organization, program))


class MaintenanceTicketCreateView(APIView):
    """Counselor POST for a new maintenance ticket."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    http_method_names = ["post", "head", "options"]

    def post(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        viewer, org, today = ctx.person, ctx.organization, ctx.today

        # ``line_items`` arrives as a JSON string under multipart (nested
        # arrays don't survive a QueryDict); normalize to a real list before
        # validation. JSON requests already provide a list.
        data = request.data.dict() if hasattr(request.data, "dict") else dict(request.data)
        raw_lines = data.get("line_items")
        if isinstance(raw_lines, str):
            stripped = raw_lines.strip()
            if stripped:
                try:
                    data["line_items"] = json.loads(stripped)
                except ValueError:
                    return Response(
                        {"line_items": "Must be a JSON array."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            else:
                data.pop("line_items", None)

        serializer = MaintenanceTicketCreateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        # Pull photos straight off ``request.FILES`` rather than through the
        # serializer; ListField + multipart don't compose (see the serializer
        # docstring). Validation happens via per-photo ImageField below.
        photos = []
        if hasattr(request.FILES, "getlist"):
            photos = request.FILES.getlist("photos")
        if photos:
            photo_validator = MaintenanceTicketPhotoUploadSerializer
            for f in photos:
                p_ser = photo_validator(data={"image": f})
                p_ser.is_valid(raise_exception=True)

        primary_membership = primary_operational_membership(viewer, today=today)
        if primary_membership is None or primary_membership.program is None:
            msg = "No active program membership."
            raise PermissionDenied(msg)
        program = primary_membership.program

        # Validate category against the configurable catalog (active
        # Maintenance-store items) plus the legacy enum values for back-compat.
        category = (payload["category"] or "").strip()
        catalog_items = list(active_items_for_role(org, program, "maintenance"))
        allowed = {it.name.casefold() for it in catalog_items}
        allowed |= {v.casefold() for v in MaintenanceTicket.Category.values}
        if category.casefold() not in allowed:
            return Response(
                {"category": f"Unknown maintenance category {category!r}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        category_item = next(
            (it for it in catalog_items if it.name.casefold() == category.casefold()),
            None,
        )

        # Resolve consumable line items up front so an invalid id fails before
        # we create the ticket.
        resolved_lines = resolve_line_items(
            org, program, "maintenance", payload.get("line_items"),
        )

        def _create_ticket():
            ticket = MaintenanceTicket(
                organization=org,
                program=program,
                submitted_by=primary_membership,
                location=payload["location"],
                category=category,
                description=payload.get("description", ""),
                urgency=payload["urgency"],
                urgent_reason=payload.get("urgent_reason", ""),
                client_submission_id=payload["client_submission_id"],
            )
            # Exclude ``category`` from model validation: the field keeps
            # ``choices=Category.choices`` for legacy back-compat, but we now
            # also accept configurable catalog item labels (already validated
            # against the catalog + enum above). full_clean()'s choice check
            # would otherwise reject any admin-defined label.
            ticket.full_clean(exclude=["category"])
            ticket.save()
            # Record the category selection as a (service) line item so the
            # planning dashboard can group maintenance requests by item/type.
            RequestLineItem.objects.create(
                organization=org,
                ticket=ticket,
                item=category_item,
                item_label=category[:120],
                quantity=1,
            )
            for line in resolved_lines:
                RequestLineItem.objects.create(
                    organization=org,
                    ticket=ticket,
                    item=line["item"],
                    item_label=line["item_label"],
                    quantity=line["quantity"],
                    note=line["note"],
                )
            for image in photos:
                TicketPhoto.objects.create(
                    ticket=ticket,
                    image=image,
                    uploaded_by=primary_membership,
                    is_followup=False,
                )
            return ticket

        try:
            ticket, created = idempotent_create(
                MaintenanceTicket,
                program=program,
                client_submission_id=payload["client_submission_id"],
                create_fn=_create_ticket,
            )
        except DjangoValidationError as e:
            return Response(
                e.message_dict if hasattr(e, "message_dict") else str(e),
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not created:
            return Response(
                maintenance_ticket_response(ticket), status=status.HTTP_200_OK,
            )

        audit_module.created(
            primary_membership,
            ticket,
            after_state=_ticket_after_state(ticket),
            content_type="maintenance_ticket",
        )

        send_ticket_created_email.delay(str(ticket.id))

        bunks = viewer_bunk_groups(viewer)
        co_ids = co_counselor_person_ids(viewer, bunks)
        invalidate_dashboard_for_viewers(org, co_ids | {viewer.id}, today)

        return Response(
            maintenance_ticket_response(ticket), status=status.HTTP_201_CREATED,
        )


class MaintenanceTicketPhotoCreateView(APIView):
    """POST a follow-up photo to an existing ticket (decision C5)."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    http_method_names = ["post", "head", "options"]

    def post(self, request, ticket_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        viewer, org = ctx.person, ctx.organization

        ticket = (
            MaintenanceTicket.all_objects.filter(id=ticket_id, organization=org)
            .select_related("submitted_by")
            .first()
        )
        if ticket is None:
            return Response(
                {"detail": "Ticket not found."}, status=status.HTTP_404_NOT_FOUND,
            )

        # Counselors may only add follow-ups to tickets THEY submitted
        # (decision C5). Cross-counselor follow-ups are out of scope until
        # bunk-team co-ownership is decided.
        viewer_membership_ids = set(
            Membership.objects.filter(person=viewer, is_active=True)
            .values_list("id", flat=True),
        )
        if ticket.submitted_by_id not in viewer_membership_ids:
            msg = "You can only add photos to tickets you submitted."
            raise PermissionDenied(msg)

        serializer = MaintenanceTicketPhotoUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        uploader_membership = (
            Membership.objects.filter(person=viewer, is_active=True)
            .order_by("-created_at")
            .first()
        )

        photo = TicketPhoto.objects.create(
            ticket=ticket,
            image=payload["image"],
            caption=payload.get("caption", ""),
            uploaded_by=uploader_membership,
            is_followup=True,
        )

        return Response(
            ticket_photo_response(photo), status=status.HTTP_201_CREATED,
        )
