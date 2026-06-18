"""Counselor maintenance ticket write endpoints (Story 8).

- ``POST /api/v1/counselor/maintenance-tickets/`` — create a ticket, optionally
  with photos attached via multipart ``photos`` fields.
- ``POST /api/v1/counselor/maintenance-tickets/<uuid>/photos/`` — add follow-up
  photos to a ticket the viewer submitted (decision C5).

Photos are stored via the configured ``DEFAULT_FILE_STORAGE`` backend: S3 in
production (with presigned URLs) and the local filesystem in dev / tests.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser
from rest_framework.parsers import JSONParser
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core import audit as audit_module
from bunk_logs.core.models import MaintenanceTicket
from bunk_logs.core.models import Membership
from bunk_logs.core.models import TicketPhoto
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


class MaintenanceTicketCreateView(APIView):
    """Counselor POST for a new maintenance ticket."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    http_method_names = ["post", "head", "options"]

    def post(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        viewer, org, today = ctx.person, ctx.organization, ctx.today

        serializer = MaintenanceTicketCreateSerializer(data=request.data)
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

        primary_membership = (
            Membership.objects.filter(person=viewer, is_active=True)
            .select_related("program")
            .order_by("-created_at")
            .first()
        )
        if primary_membership is None or primary_membership.program is None:
            msg = "No active program membership."
            raise PermissionDenied(msg)
        program = primary_membership.program

        def _create_ticket():
            ticket = MaintenanceTicket(
                organization=org,
                program=program,
                submitted_by=primary_membership,
                location=payload["location"],
                category=payload["category"],
                description=payload.get("description", ""),
                urgency=payload["urgency"],
                urgent_reason=payload.get("urgent_reason", ""),
                client_submission_id=payload["client_submission_id"],
            )
            ticket.full_clean()
            ticket.save()
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
