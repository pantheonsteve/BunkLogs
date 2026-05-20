"""Admin-only HTTP surface for the cross-cutting audit trail (Step 7_4).

Three read endpoints, all gated by :class:`IsOrgAdminOrSuperuser`. They
return events from the org-scoped ``AuditEvent.objects`` manager so a
tenant Admin can only ever see their own org's history (Super Admins,
who can switch orgs via the standard X-Organization header / context,
see whichever org is currently active).

Per the spec, viewing an audit trail is itself an audited action: the
``GET /audit/`` (by content) endpoint writes an ``AUDIT_VIEW`` event for
each viewed content row. The other two endpoints are aggregate views
that intentionally do not log meta-audits (matches Story 59 wording,
which scopes meta-audit to per-content-trail viewing).
"""

from __future__ import annotations

from datetime import datetime
from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from bunk_logs.core import audit as audit_module
from bunk_logs.core.models import AuditEvent
from bunk_logs.core.models import Membership
from bunk_logs.core.permissions import IsOrgAdminOrSuperuser


class _AuditTargetStub:
    """Lightweight stand-in passed to :func:`audit.audit_view`.

    The audit-view meta-event needs an organization + content_type + content_id
    but does NOT need to load the underlying content row (which may not even
    exist anymore). This stub satisfies the helper's duck-typed contract.
    """

    def __init__(self, *, organization, content_type: str, content_id: str):
        self.organization = organization
        self.program = None
        self.id = content_id
        self._content_type_label_value = content_type

    def _audit_content_type_label(self) -> str:  # pragma: no cover - trivial
        return self._content_type_label_value


class AuditEventSerializer(serializers.ModelSerializer):
    actor_membership = serializers.PrimaryKeyRelatedField(read_only=True)
    actor_user = serializers.PrimaryKeyRelatedField(read_only=True)
    organization = serializers.PrimaryKeyRelatedField(read_only=True)
    program = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = AuditEvent
        fields = [
            "id",
            "created_at",
            "event_type",
            "content_type",
            "content_id",
            "organization",
            "program",
            "actor_membership",
            "actor_user",
            "before_state",
            "after_state",
            "reason_note",
            "is_admin_override",
            "metadata",
        ]
        read_only_fields = fields


class AuditEventViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only ViewSet exposing audit history to org Admins.

    Routes:

    * ``GET /api/v1/audit/?content_type=<type>&content_id=<id>`` --
      chronological trail for a specific content row. Both query params
      are required; missing one returns 400. Writes ``AUDIT_VIEW``.
    * ``GET /api/v1/audit/by-actor/?membership_id=<id>`` -- events for a
      given actor Membership. Returned in newest-first order.
    * ``GET /api/v1/audit/admin-overrides/?since=<YYYY-MM-DD>`` -- all
      admin-override events (``is_admin_override=True``) since the given
      date (defaults to 30 days ago, mirroring the spec's example).
    """

    serializer_class = AuditEventSerializer
    permission_classes = [IsOrgAdminOrSuperuser]
    pagination_class = None  # explicit: small per-content trails by default

    def get_queryset(self):
        # ``AuditEvent.objects`` is org-scoped (see managers.AuditEventScopedManager).
        return AuditEvent.objects.select_related(
            "actor_membership__person",
            "program",
        )

    def _actor_for_request(self):
        """Find the active Admin Membership for the request user, if any."""
        person_id = getattr(self.request.user, "person_id", None)
        if person_id is None:
            from bunk_logs.core.models import Person

            person = Person.objects.filter(user=self.request.user).first()
            if person is None:
                return self.request.user
            person_id = person.id
        membership = (
            Membership.objects.filter(
                person_id=person_id, role="admin", is_active=True,
            )
            .order_by("-created_at")
            .first()
        )
        return membership or self.request.user

    def list(self, request, *args, **kwargs):
        content_type = (request.query_params.get("content_type") or "").strip()
        content_id = (request.query_params.get("content_id") or "").strip()
        if not content_type or not content_id:
            return Response(
                {
                    "detail": (
                        "Both 'content_type' and 'content_id' query params are required."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs = (
            self.get_queryset()
            .filter(content_type=content_type, content_id=content_id)
            .order_by("created_at")
        )
        data = self.get_serializer(qs, many=True).data
        # Meta-audit: log that the trail was viewed (Story 59 criterion 10).
        org = getattr(request, "organization", None) or _org_from_first_event(qs)
        if org is not None:
            audit_module.audit_view(
                self._actor_for_request(),
                _AuditTargetStub(
                    organization=org,
                    content_type=content_type,
                    content_id=content_id,
                ),
            )
        return Response(data)

    @action(detail=False, methods=["get"], url_path="by-actor")
    def by_actor(self, request):
        raw = (request.query_params.get("membership_id") or "").strip()
        if not raw.isdigit():
            return Response(
                {"detail": "membership_id query param is required (integer)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs = (
            self.get_queryset()
            .filter(actor_membership_id=int(raw))
            .order_by("-created_at")
        )
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=False, methods=["get"], url_path="admin-overrides")
    def admin_overrides(self, request):
        since_raw = (request.query_params.get("since") or "").strip()
        if since_raw:
            try:
                since = datetime.fromisoformat(since_raw).date()
            except ValueError:
                return Response(
                    {"detail": "'since' must be ISO date (YYYY-MM-DD)."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            since = (timezone.now() - timedelta(days=30)).date()

        qs = (
            self.get_queryset()
            .filter(is_admin_override=True, created_at__date__gte=since)
            .order_by("-created_at")
        )
        return Response(self.get_serializer(qs, many=True).data)


def _org_from_first_event(qs):
    """Fallback org lookup for meta-audit when request.organization is absent."""
    first = qs.first()
    return first.organization if first else None
