"""HTTP layer for the Supervision primitive (Step 7_3).

Admin-only ViewSet exposing the four supervision patterns documented in
``backend/bunk_logs/core/SUPERVISION.md``. Mutations are tightly constrained:

* ``POST`` creates a new Supervision row (Admin can set any combination of
  target fields valid for the chosen ``target_type``).
* ``PATCH`` is end-date-only after creation -- supervisor and target are
  immutable per the canonical spec (Story 56 decision 4). All other fields
  are silently ignored.
* ``DELETE`` is intentionally not implemented; soft-end via ``end_date``.

Every mutation writes a ``SupervisionEvent`` so the audit trail (Step 7_4)
has a complete forward-compatible log.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework import status
from rest_framework import viewsets
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.response import Response

from bunk_logs.core import audit as audit_module
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Program
from bunk_logs.core.models import Supervision
from bunk_logs.core.models import record_supervision_event
from bunk_logs.core.models import supervision_snapshot
from bunk_logs.core.permissions import IsOrgAdminOrSuperuser
from bunk_logs.core.permissions import _person_for_request


class SupervisionSerializer(serializers.ModelSerializer):
    """Read serializer + create payload validator.

    Update operations are routed through :meth:`SupervisionViewSet.partial_update`
    and only touch ``end_date``; this serializer's writable fields apply to
    create only.
    """

    is_active = serializers.SerializerMethodField()
    supervisor_membership = serializers.PrimaryKeyRelatedField(
        queryset=Membership.all_objects.all(),
    )
    target_membership = serializers.PrimaryKeyRelatedField(
        queryset=Membership.all_objects.all(),
        required=False,
        allow_null=True,
    )
    target_program = serializers.PrimaryKeyRelatedField(
        queryset=Program.all_objects.all(),
        required=False,
        allow_null=True,
    )
    target_bunk = serializers.PrimaryKeyRelatedField(
        queryset=AssignmentGroup.all_objects.all(),
        required=False,
        allow_null=True,
    )
    target_role = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Supervision
        fields = [
            "id",
            "supervisor_membership",
            "target_type",
            "target_membership",
            "target_role",
            "target_program",
            "target_bunk",
            "start_date",
            "end_date",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_active", "created_at", "updated_at"]

    def get_is_active(self, obj) -> bool:
        return obj.is_active()


class SupervisionViewSet(viewsets.ModelViewSet):
    """Admin-only CRUD surface for ``Supervision`` rows.

    See module docstring for the mutation contract. The queryset uses
    ``Supervision.objects`` (org-scoped manager) so cross-tenant rows are
    unreachable even with a known supervisor_membership_id.
    """

    serializer_class = SupervisionSerializer
    permission_classes = [IsOrgAdminOrSuperuser]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = Supervision.objects.select_related(
            "supervisor_membership__person",
            "supervisor_membership__program",
            "target_membership__person",
            "target_program",
            "target_bunk",
        )
        params = self.request.query_params

        sup_id = (params.get("supervisor_membership_id") or "").strip()
        if sup_id:
            qs = qs.filter(supervisor_membership_id=sup_id)

        target_type = (params.get("target_type") or "").strip()
        if target_type:
            qs = qs.filter(target_type=target_type)

        active_filter = (params.get("is_active") or "").strip().lower()
        if active_filter in {"true", "1", "yes"}:
            qs = qs.active()
        elif active_filter in {"false", "0", "no"}:
            from django.utils import timezone

            today = timezone.now().date()
            qs = qs.exclude(start_date__lte=today, end_date=None).exclude(
                start_date__lte=today, end_date__gte=today,
            )

        return qs.order_by("-created_at")

    def destroy(self, request, *args, **kwargs):
        # Per spec: no delete, soft-end via PATCH end_date instead.
        method = "DELETE"
        raise MethodNotAllowed(method)

    def update(self, request, *args, **kwargs):
        # Block full PUT: only PATCH end_date is supported.
        method = "PUT"
        raise MethodNotAllowed(method)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        instance = Supervision(**serializer.validated_data)
        try:
            instance.save()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict or {"detail": exc.messages})

        actor = _person_for_request(request)
        actor_membership = (
            Membership.objects.filter(
                person=actor, role="admin", is_active=True,
            ).first()
            if actor
            else None
        )
        record_supervision_event(
            supervision=instance,
            event_type="created",
            actor_membership=actor_membership,
            actor_user=request.user if request.user.is_authenticated else None,
            after_state=supervision_snapshot(instance),
        )
        # Dual-write to the cross-cutting AuditEvent (Step 7_4). SupervisionEvent
        # stays in place for query-helper continuity until backfilled & dropped.
        audit_module.created(
            actor_membership or (request.user if request.user.is_authenticated else None),
            instance,
            after_state=supervision_snapshot(instance),
            content_type="supervision",
        )

        return Response(
            self.get_serializer(instance).data,
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        instance = get_object_or_404(self.get_queryset(), pk=kwargs.get("pk"))

        immutable_provided = [
            f
            for f in (
                "supervisor_membership",
                "target_type",
                "target_membership",
                "target_role",
                "target_program",
                "target_bunk",
                "start_date",
            )
            if f in request.data
        ]
        if immutable_provided:
            return Response(
                {
                    f: "This field is immutable after creation; only end_date may be patched."
                    for f in immutable_provided
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if "end_date" not in request.data:
            return Response(
                {"end_date": "PATCH must include end_date."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        before = supervision_snapshot(instance)
        new_end_date = request.data.get("end_date")
        instance.end_date = new_end_date or None
        try:
            instance.save()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict or {"detail": exc.messages})

        after = supervision_snapshot(instance)
        actor = _person_for_request(request)
        actor_membership = (
            Membership.objects.filter(
                person=actor, role="admin", is_active=True,
            ).first()
            if actor
            else None
        )
        event_type = "ended" if instance.end_date is not None else "modified"
        record_supervision_event(
            supervision=instance,
            event_type=event_type,
            actor_membership=actor_membership,
            actor_user=request.user if request.user.is_authenticated else None,
            before_state=before,
            after_state=after,
        )
        audit_actor = actor_membership or (
            request.user if request.user.is_authenticated else None
        )
        if instance.end_date is not None:
            audit_module.deactivated(
                audit_actor,
                instance,
                before_state=before,
                after_state=after,
                content_type="supervision",
                reason=(request.data.get("reason") or "").strip(),
            )
        else:
            audit_module.edited(
                audit_actor,
                instance,
                before,
                after,
                content_type="supervision",
            )

        return Response(self.get_serializer(instance).data)
