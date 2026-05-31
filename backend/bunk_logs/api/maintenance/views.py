"""Maintenance staff queue, ticket detail, and notes (Step 7_10, Stories 30-35).

Endpoints
---------
GET  /api/v1/maintenance/queue/              — active/closed queue with filters
GET  /api/v1/maintenance/tickets/<id>/       — full ticket detail + activity
POST /api/v1/maintenance/tickets/<id>/notes/ — add note
PATCH /api/v1/maintenance/tickets/<id>/notes/<note_id>/ — edit within 24h
GET  /api/v1/maintenance/notes/audience/     — audience disclosure labels

Notes use :class:`~bunk_logs.core.models.OrderActivityEvent` with
``event_type='note'``.  Visibility is stored in ``metadata["visibility"]``
(``"team_only"`` | ``"submitter_visible"``).
"""

from __future__ import annotations

import logging
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status as http_status
from rest_framework.exceptions import NotFound
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.api.counselor.serializers import MaintenanceTicketPhotoUploadSerializer
from bunk_logs.core.models import MaintenanceTicket
from bunk_logs.core.models import OrderActivityEvent
from bunk_logs.core.models import TicketPhoto

from .common import resolve_queue_viewer
from .common import viewer_or_403

logger = logging.getLogger(__name__)

NOTE_EDIT_WINDOW = timedelta(hours=24)

URGENCY_ORDER: dict[str, int] = {"urgent": 0, "normal": 1, "low": 2, "": 3}

STATUS_OPEN = (
    MaintenanceTicket.Status.NEW,
    MaintenanceTicket.Status.IN_PROGRESS,
)
STATUS_CLOSED = (
    MaintenanceTicket.Status.FULFILLED,
    MaintenanceTicket.Status.UNABLE_TO_FULFILL,
)

VALID_FILTERS = frozenset({"open", "new", "in_progress", "closed", "all"})
VALID_VISIBILITY = frozenset({"team_only", "submitter_visible"})


# ---------------------------------------------------------------------------
# Queue
# ---------------------------------------------------------------------------


class MaintenanceQueueView(APIView):
    """``GET /api/v1/maintenance/queue/`` — maintenance ticket queue.

    Query params:

    * ``filter`` — ``open`` (default), ``new``, ``in_progress``, ``closed``, ``all``
    * ``search`` — free-text search (description + note bodies); closed only
    * ``date_from`` / ``date_to`` — YYYY-MM-DD; closed filter date clamp
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx, scope = resolve_queue_viewer(request)
        filt = (request.query_params.get("filter") or "open").lower()
        if filt not in VALID_FILTERS:
            raise ValidationError({"filter": f"Must be one of: {', '.join(sorted(VALID_FILTERS))}."})

        # Everyone sees the full program queue; ``viewer`` scope just renders it
        # read-only (transition actions are stripped in ``_ticket_row``).
        base = MaintenanceTicket.objects.select_related(
            "submitted_by__person", "last_transition_by__person",
        ).filter(program=ctx.program)

        qs = base
        if filt == "open":
            qs = qs.filter(status__in=STATUS_OPEN)
        elif filt == "new":
            qs = qs.filter(status=MaintenanceTicket.Status.NEW)
        elif filt == "in_progress":
            qs = qs.filter(status=MaintenanceTicket.Status.IN_PROGRESS)
        elif filt == "closed":
            qs = qs.filter(status__in=STATUS_CLOSED)
            qs = _apply_closed_filters(qs, request)
        # "all" — no status filter

        tickets = list(qs)

        if filt in ("open", "new", "in_progress", "all"):
            tickets.sort(key=lambda t: (URGENCY_ORDER.get(t.urgency, 3), t.created_at))
        else:
            tickets.sort(key=lambda t: t.updated_at, reverse=True)

        counts = _build_counts(base)
        rows = [_ticket_row(t, scope=scope) for t in tickets]

        return Response({"tickets": rows, "counts": counts, "scope": scope})


def _apply_closed_filters(qs, request):
    search = (request.query_params.get("search") or "").strip()
    date_from_raw = request.query_params.get("date_from")
    date_to_raw = request.query_params.get("date_to")

    if date_from_raw:
        d = parse_date(date_from_raw)
        if d is None:
            raise ValidationError({"date_from": "Expected YYYY-MM-DD."})
        qs = qs.filter(updated_at__date__gte=d)
    if date_to_raw:
        d = parse_date(date_to_raw)
        if d is None:
            raise ValidationError({"date_to": "Expected YYYY-MM-DD."})
        qs = qs.filter(updated_at__date__lte=d)

    if search:
        # Match on ticket description; note bodies matched via a subquery
        note_ticket_ids = list(
            OrderActivityEvent.objects.filter(
                content_type="maintenance_ticket",
                event_type=OrderActivityEvent.EventType.NOTE,
                note__icontains=search,
            ).values_list("content_id", flat=True).distinct(),
        )
        qs = qs.filter(
            Q(description__icontains=search)
            | Q(location__icontains=search)
            | Q(category__icontains=search)
            | Q(id__in=note_ticket_ids),
        )

    return qs


def _build_counts(base_qs) -> dict:
    """Header counts over the scope's base queryset (program or submitter)."""
    new_count = base_qs.filter(status=MaintenanceTicket.Status.NEW).count()
    in_progress_count = base_qs.filter(status=MaintenanceTicket.Status.IN_PROGRESS).count()
    urgent_open_count = base_qs.filter(
        status__in=STATUS_OPEN, urgency=MaintenanceTicket.Urgency.URGENT,
    ).count()
    return {
        "new": new_count,
        "in_progress": in_progress_count,
        "urgent_open": urgent_open_count,
    }


def _ticket_row(ticket: MaintenanceTicket, *, scope: str = "team") -> dict:
    submitter = ticket.submitted_by
    submitter_person = getattr(submitter, "person", None) if submitter else None
    age_seconds = int((timezone.now() - ticket.created_at).total_seconds()) if ticket.created_at else None
    has_photos = TicketPhoto.all_objects.filter(ticket=ticket).exists()

    acknowledger: dict | None = None
    if ticket.last_transition_by_id and ticket.status == MaintenanceTicket.Status.IN_PROGRESS:
        ack_membership = ticket.last_transition_by
        ack_person = getattr(ack_membership, "person", None) if ack_membership else None
        acknowledger = {
            "name": ack_person.full_name if ack_person else None,
            "at": ticket.last_transition_at.isoformat() if ticket.last_transition_at else None,
        }

    # Who resolved a closed ticket (fulfilled / unable to fulfill), for the
    # queue card's "Fulfilled: 2d ago by Mike R" line.
    resolution: dict | None = None
    if ticket.last_transition_by_id and ticket.status in STATUS_CLOSED:
        res_membership = ticket.last_transition_by
        res_person = getattr(res_membership, "person", None) if res_membership else None
        resolution = {
            "name": res_person.full_name if res_person else None,
            "at": ticket.last_transition_at.isoformat() if ticket.last_transition_at else None,
        }

    return {
        "id": str(ticket.id),
        "status": ticket.status,
        "urgency": ticket.urgency,
        "location": ticket.location,
        "category": ticket.category,
        "description": (ticket.description or "")[:120],
        "submitter_name": (
            f"{submitter_person.first_name} {submitter_person.last_name}".strip()
            if submitter_person else None
        ),
        "age_seconds": age_seconds,
        "has_photos": has_photos,
        "acknowledger": acknowledger,
        "resolution": resolution,
        # Non-team viewers get a read-only view — no transition actions.
        "available_transitions": ticket.available_transitions() if scope == "team" else [],
        "is_within_correction_window": ticket.can_correct_last_transition(),
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
    }


# ---------------------------------------------------------------------------
# Ticket detail
# ---------------------------------------------------------------------------


class MaintenanceTicketDetailView(APIView):
    """``GET /api/v1/maintenance/tickets/<id>/`` — full ticket detail."""

    permission_classes = [IsAuthenticated]

    def get(self, request, ticket_id, *args, **kwargs):
        # Any active member can open a ticket to follow its progress; ``viewer``
        # scope is read-only (no actions) and can't see team-only notes.
        ctx, scope = resolve_queue_viewer(request)
        ticket = MaintenanceTicket.objects.filter(
            pk=ticket_id, program=ctx.program,
        ).select_related("submitted_by__person", "last_transition_by__person").first()
        if ticket is None:
            msg = "Ticket not found."
            raise NotFound(msg)

        photos = list(
            TicketPhoto.all_objects.filter(ticket=ticket)
            .select_related("uploaded_by__person")
            .order_by("created_at"),
        )
        activity = list(
            OrderActivityEvent.objects.filter(
                content_type="maintenance_ticket", content_id=ticket.id,
            )
            .select_related("actor_membership__person")
            .order_by("created_at"),
        )
        if scope != "team":
            # Hide internal "team only" notes from non-maintenance viewers; the
            # progress (state changes, corrections, submitter-visible notes) stays.
            activity = [e for e in activity if not _is_team_only_note(e)]

        return Response({
            "ticket": _ticket_detail_payload(ticket, scope=scope),
            "photos": [_photo_payload(p) for p in photos],
            "activity": [_activity_event_payload(e) for e in activity],
            "scope": scope,
        })


def _is_team_only_note(event: OrderActivityEvent) -> bool:
    if event.event_type != OrderActivityEvent.EventType.NOTE:
        return False
    visibility = event.metadata.get("visibility", "team_only") if event.metadata else "team_only"
    return visibility == "team_only"


def _ticket_detail_payload(ticket: MaintenanceTicket, *, scope: str = "team") -> dict:
    submitter = ticket.submitted_by
    submitter_person = getattr(submitter, "person", None) if submitter else None
    return {
        "id": str(ticket.id),
        "status": ticket.status,
        "urgency": ticket.urgency,
        "urgent_reason": ticket.urgent_reason,
        "location": ticket.location,
        "category": ticket.category,
        "description": ticket.description,
        "title": ticket.title,
        "submitter_name": (
            f"{submitter_person.first_name} {submitter_person.last_name}".strip()
            if submitter_person else None
        ),
        "submitted_by_membership_id": str(ticket.submitted_by_id) if ticket.submitted_by_id else None,
        # Non-team viewers get a read-only payload — no transitions or undo.
        "available_transitions": ticket.available_transitions() if scope == "team" else [],
        "is_within_correction_window": ticket.can_correct_last_transition() if scope == "team" else False,
        "last_transition_at": (
            ticket.last_transition_at.isoformat() if ticket.last_transition_at else None
        ),
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
    }


def _photo_payload(photo: TicketPhoto) -> dict:
    uploader = photo.uploaded_by
    uploader_person = getattr(uploader, "person", None) if uploader else None
    return {
        "id": str(photo.id),
        "image_url": photo.image.url if photo.image else None,
        "caption": photo.caption,
        "is_followup": photo.is_followup,
        "uploaded_by": (
            f"{uploader_person.first_name} {uploader_person.last_name}".strip()
            if uploader_person else None
        ),
        "created_at": photo.created_at.isoformat() if photo.created_at else None,
    }


def _activity_event_payload(event: OrderActivityEvent) -> dict:
    actor_person = None
    if event.actor_membership:
        actor_person = getattr(event.actor_membership, "person", None)
    visibility = event.metadata.get("visibility", "team_only") if event.metadata else "team_only"
    is_editable = (
        event.event_type == OrderActivityEvent.EventType.NOTE
        and (timezone.now() - event.created_at) <= NOTE_EDIT_WINDOW
    )
    return {
        "id": str(event.id),
        "event_type": event.event_type,
        "from_state": event.from_state,
        "to_state": event.to_state,
        "note": event.note,
        "reason": event.reason,
        "visibility": visibility,
        "actor_name": actor_person.full_name if actor_person else None,
        "actor_membership_id": str(event.actor_membership_id) if event.actor_membership_id else None,
        "is_within_edit_window": is_editable,
        "correction_of": str(event.correction_of_id) if event.correction_of_id else None,
        "created_at": event.created_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------


class MaintenanceNoteCreateView(APIView):
    """``POST /api/v1/maintenance/tickets/<id>/notes/`` — add a note.

    Body: ``{ "body": "...", "visibility": "team_only"|"submitter_visible" }``
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, ticket_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        ticket = _get_ticket_or_404(ticket_id, ctx.program)

        if ticket.status in STATUS_CLOSED:
            return Response(
                {"detail": "Cannot add notes to a closed ticket. Reopen it first."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        data = request.data or {}
        body = (data.get("body") or "").strip()
        visibility = (data.get("visibility") or "team_only").strip()

        errors: dict[str, str] = {}
        if not body:
            errors["body"] = "Required."
        if visibility not in VALID_VISIBILITY:
            errors["visibility"] = f"Must be one of: {', '.join(sorted(VALID_VISIBILITY))}."
        if errors:
            return Response(errors, status=http_status.HTTP_400_BAD_REQUEST)

        event = OrderActivityEvent.objects.create(
            organization=ctx.organization,
            program=ctx.program,
            actor_membership=ctx.membership,
            actor_user=request.user,
            event_type=OrderActivityEvent.EventType.NOTE,
            content_type="maintenance_ticket",
            content_id=ticket.id,
            note=body,
            metadata={"visibility": visibility},
        )

        return Response(_activity_event_payload(event), status=http_status.HTTP_201_CREATED)


class MaintenanceNoteDetailView(APIView):
    """``PATCH /api/v1/maintenance/tickets/<id>/notes/<note_id>/`` — edit within 24h."""

    permission_classes = [IsAuthenticated]

    def patch(self, request, ticket_id, note_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        _get_ticket_or_404(ticket_id, ctx.program)

        event = OrderActivityEvent.objects.filter(
            pk=note_id,
            content_type="maintenance_ticket",
            content_id=ticket_id,
            event_type=OrderActivityEvent.EventType.NOTE,
        ).first()
        if event is None:
            msg = "Note not found."
            raise NotFound(msg)

        if event.actor_membership_id != ctx.membership.id:
            msg = "Only the original author may edit a note."
            raise PermissionDenied(msg)

        if (timezone.now() - event.created_at) > NOTE_EDIT_WINDOW:
            msg = "This note can no longer be edited (24h window has closed)."
            raise PermissionDenied(msg)

        data = request.data or {}
        if "body" in data:
            body = (data.get("body") or "").strip()
            if not body:
                return Response({"body": "Cannot be empty."}, status=http_status.HTTP_400_BAD_REQUEST)
            event.note = body
        if "visibility" in data:
            visibility = (data.get("visibility") or "").strip()
            if visibility not in VALID_VISIBILITY:
                return Response(
                    {"visibility": f"Must be one of: {', '.join(sorted(VALID_VISIBILITY))}."},
                    status=http_status.HTTP_400_BAD_REQUEST,
                )
            event.metadata = {**(event.metadata or {}), "visibility": visibility}

        event.save(update_fields=["note", "metadata"])
        return Response(_activity_event_payload(event))


class MaintenanceNoteAudienceView(APIView):
    """``GET /api/v1/maintenance/notes/audience/?visibility=<>`` — disclosure copy."""

    permission_classes = [IsAuthenticated]

    _LABELS: dict[str, str] = {
        "team_only": "This note will be visible to: Maintenance team, Admin.",
        "submitter_visible": (
            "This note will be visible to: Submitting counselor, Unit Head, "
            "Maintenance team, Leadership Team, Admin."
        ),
    }

    def get(self, request, *args, **kwargs):
        viewer_or_403(request)
        visibility = (request.query_params.get("visibility") or "team_only").strip()
        if visibility not in VALID_VISIBILITY:
            visibility = "team_only"
        return Response({"visibility": visibility, "label": self._LABELS[visibility]})


# ---------------------------------------------------------------------------
# Follow-up photo upload (maintenance team)
# ---------------------------------------------------------------------------


class MaintenanceTicketPhotoCreateView(APIView):
    """``POST /api/v1/maintenance/tickets/<id>/photos/`` — upload a follow-up photo.

    Accepts multipart/form-data with ``image`` (required) and ``caption``
    (optional). Marks the photo ``is_followup=True`` so the detail view can
    render it in activity order distinct from the original submission photos.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    http_method_names = ["post", "head", "options"]

    def post(self, request, ticket_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        ticket = _get_ticket_or_404(ticket_id, ctx.program)

        serializer = MaintenanceTicketPhotoUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        photo = TicketPhoto.objects.create(
            ticket=ticket,
            image=payload["image"],
            caption=payload.get("caption", ""),
            uploaded_by=ctx.membership,
            is_followup=True,
        )
        return Response(_photo_payload(photo), status=http_status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_ticket_or_404(ticket_id, program) -> MaintenanceTicket:
    ticket = MaintenanceTicket.objects.filter(
        pk=ticket_id, program=program,
    ).first()
    if ticket is None:
        msg = "Ticket not found."
        raise NotFound(msg)
    return ticket
