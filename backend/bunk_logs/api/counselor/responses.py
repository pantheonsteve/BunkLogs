"""Shared response shapers for counselor write endpoints.

Consolidated so create / patch responses across all four resources agree on
the same camper, ticket, and reflection payloads — and so the list endpoints
(7_6b) and write endpoints (7_6c) can converge over time.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bunk_logs.core.content_visibility import audience_labels
from bunk_logs.core.content_visibility import reflection_content_type
from bunk_logs.core.content_visibility import reflection_is_private

if TYPE_CHECKING:
    from bunk_logs.core.models import MaintenanceTicket
    from bunk_logs.core.models import Order
    from bunk_logs.core.models import Reflection
    from bunk_logs.core.models import TicketPhoto


def reflection_response(reflection: Reflection) -> dict:
    """Counselor-facing reflection payload.

    Includes ``audience`` so the client can render the AudienceDisclosure
    component without a separate call (Step 7_6 item 11). Computed server-side
    because the role -> label mapping is i18n-managed in core.
    """
    audience = audience_labels(
        reflection_content_type(reflection),
        is_sensitive=bool(reflection.is_sensitive),
        is_private=reflection_is_private(reflection),
    )
    return {
        "id": reflection.id,
        "subject_id": reflection.subject_id,
        "author_id": reflection.author_id,
        "assignment_group_id": reflection.assignment_group_id,
        "template": {
            "id": reflection.template_id,
            "slug": reflection.template.slug if reflection.template_id else None,
            "version": reflection.template.version if reflection.template_id else None,
        },
        "client_submission_id": (
            str(reflection.client_submission_id)
            if reflection.client_submission_id
            else None
        ),
        "answers": reflection.answers,
        "language": reflection.language,
        "team_visibility": reflection.team_visibility,
        "is_complete": reflection.is_complete,
        "period_start": reflection.period_start.isoformat(),
        "period_end": reflection.period_end.isoformat(),
        "submitted_at": (
            reflection.submitted_at.isoformat() if reflection.submitted_at else None
        ),
        "updated_at": (
            reflection.updated_at.isoformat() if reflection.updated_at else None
        ),
        "audience": audience,
    }


def order_response(order: Order) -> dict:
    """Counselor-facing camper-care request payload."""
    return {
        "id": str(order.id),
        "status": order.status,
        "subject_id": order.subject_id,
        "submitted_by_id": order.submitted_by_id,
        "item": order.item,
        "item_note": order.item_note,
        "description": order.description,
        "client_submission_id": (
            str(order.client_submission_id) if order.client_submission_id else None
        ),
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
    }


def ticket_photo_response(photo: TicketPhoto) -> dict:
    """Maintenance ticket photo payload.

    The ``image`` URL is whatever the configured storage backend returns —
    a presigned S3 URL in production (``AWS_QUERYSTRING_AUTH=True``) and a
    local ``/media/`` path in dev / tests.
    """
    return {
        "id": str(photo.id),
        "image_url": photo.image.url if photo.image else None,
        "caption": photo.caption,
        "is_followup": photo.is_followup,
        "created_at": photo.created_at.isoformat() if photo.created_at else None,
    }


def maintenance_ticket_response(ticket: MaintenanceTicket) -> dict:
    """Counselor-facing maintenance ticket payload (including photos)."""
    photos = [ticket_photo_response(p) for p in ticket.photos.all()]
    return {
        "id": str(ticket.id),
        "status": ticket.status,
        "location": ticket.location,
        "category": ticket.category,
        "description": ticket.description,
        "urgency": ticket.urgency,
        "urgent_reason": ticket.urgent_reason,
        "submitted_by_id": ticket.submitted_by_id,
        "client_submission_id": (
            str(ticket.client_submission_id) if ticket.client_submission_id else None
        ),
        "photos": photos,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
    }
