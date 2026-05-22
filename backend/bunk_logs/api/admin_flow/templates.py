"""Admin Templates oversight (Step 7_13 PR3, Story 57).

``GET /api/v1/admin/templates/`` returns every ``ReflectionTemplate``
in the org regardless of author, grouped by status (Draft / Published
/ Archived / System), plus a `pending_review` flag for templates
published in the last 14 days that haven't been marked as reviewed.

``POST /api/v1/admin/templates/<id>/review/`` marks a template as
``reviewed`` or ``needs_revision`` and stamps the timestamp into
``ReflectionTemplate.metadata`` (``review_status`` /
``reviewed_at`` / ``reviewed_by_membership_id`` /
``review_note``). We use the existing ``metadata`` JSONField rather
than introducing a new column so this lands without a migration.
"""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core import audit as audit_module
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.permissions import IsOrgAdminOrSuperuser

from .common import viewer_or_403

PENDING_REVIEW_LOOKBACK_DAYS = 14
REVIEW_STATUSES = ("reviewed", "needs_revision")


def _serialize_template(t: ReflectionTemplate, *, pending_cutoff) -> dict:
    metadata = t.metadata or {}
    review_status = metadata.get("review_status")
    is_pending = (
        t.status == ReflectionTemplate.Status.PUBLISHED
        and t.published_at is not None
        and t.published_at >= pending_cutoff
        and review_status not in REVIEW_STATUSES
    )
    return {
        "id": t.id,
        "name": t.name,
        "slug": t.slug,
        "status": t.status,
        "role": t.role,
        "cadence": t.cadence,
        "program_type": t.program_type,
        "subject_mode": t.subject_mode,
        "version": t.version,
        "published_at": t.published_at.isoformat() if t.published_at else None,
        "languages": t.languages or [],
        "pending_review": is_pending,
        "review_status": review_status,
        "reviewed_at": metadata.get("reviewed_at"),
        "reviewed_by_membership_id": metadata.get("reviewed_by_membership_id"),
        "review_note": metadata.get("review_note", ""),
    }


class AdminTemplatesListView(APIView):
    permission_classes = [IsOrgAdminOrSuperuser]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        qs = ReflectionTemplate.all_objects.filter(
            organization=ctx.organization,
        ).order_by("-published_at", "-id")
        pending_cutoff = timezone.now() - timedelta(days=PENDING_REVIEW_LOOKBACK_DAYS)
        all_rows = [_serialize_template(t, pending_cutoff=pending_cutoff) for t in qs]
        grouped: dict[str, list[dict]] = {
            "draft": [], "published": [], "archived": [], "system": [],
        }
        for r in all_rows:
            grouped.setdefault(r["status"], []).append(r)
        return Response({
            "results": all_rows,
            "grouped": grouped,
            "pending_review_count": sum(1 for r in all_rows if r["pending_review"]),
        })


class AdminTemplateReviewView(APIView):
    """``POST /admin/templates/<id>/review/`` — mark Reviewed / Needs revision."""

    permission_classes = [IsOrgAdminOrSuperuser]

    def post(self, request, template_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        try:
            template = ReflectionTemplate.all_objects.get(
                pk=template_id, organization=ctx.organization,
            )
        except (ReflectionTemplate.DoesNotExist, ValueError):
            return Response(
                {"detail": "Template not found in this org."},
                status=status.HTTP_404_NOT_FOUND,
            )
        review_status = (request.data.get("review_status") or "").strip()
        if review_status not in REVIEW_STATUSES:
            return Response(
                {"detail": f"review_status must be one of {REVIEW_STATUSES}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        note = (request.data.get("review_note") or "").strip()
        before_meta = dict(template.metadata or {})
        new_meta = dict(before_meta)
        new_meta.update({
            "review_status": review_status,
            "reviewed_at": timezone.now().isoformat(),
            "reviewed_by_membership_id": ctx.membership.id if ctx.membership else None,
            "review_note": note,
        })
        template.metadata = new_meta
        template.save(update_fields=["metadata"])
        audit_module.edited(
            ctx.membership or request.user, template,
            {"review_status": before_meta.get("review_status")},
            {"review_status": review_status},
            content_type="reflection_template",
            metadata={"review_note": note} if note else None,
        )
        pending_cutoff = timezone.now() - timedelta(days=PENDING_REVIEW_LOOKBACK_DAYS)
        return Response(_serialize_template(template, pending_cutoff=pending_cutoff))
