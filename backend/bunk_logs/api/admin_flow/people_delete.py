"""Admin Person delete — preview and apply discard without merging to a winner."""

from __future__ import annotations

from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core import audit as audit_module
from bunk_logs.core.permissions import IsOrgAdminOrSuperuser
from bunk_logs.core.person_merge import discard_person
from bunk_logs.core.person_merge import plan_discard_person
from bunk_logs.core.person_merge import serialize_discard_plan

from .common import viewer_or_403
from .people import _get_person_or_404
from .people import _not_found
from .people import _person_snapshot
from .people import _serialize_person


def _build_delete_response(*, person, plan) -> dict:
    payload = serialize_discard_plan(plan)
    payload["person_id"] = person.pk
    payload["person"] = _serialize_person(person, include_memberships=True)
    return payload


class AdminPersonDeletePreviewView(APIView):
    permission_classes = [IsOrgAdminOrSuperuser]

    def post(self, request, person_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        person = _get_person_or_404(ctx, person_id)
        if person is None:
            return _not_found("Person")

        confirm_destructive = bool((request.data or {}).get("confirm_destructive"))
        plan = plan_discard_person(person=person, confirm_destructive=confirm_destructive)
        payload = _build_delete_response(person=person, plan=plan)
        if not plan.ok:
            return Response(payload, status=status.HTTP_409_CONFLICT)
        return Response(payload)


class AdminPersonDeleteApplyView(APIView):
    permission_classes = [IsOrgAdminOrSuperuser]

    def post(self, request, person_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        person = _get_person_or_404(ctx, person_id)
        if person is None:
            return _not_found("Person")

        data = request.data or {}
        reason = (data.get("reason") or "").strip()
        if not reason:
            return Response({"detail": "reason is required."}, status=status.HTTP_400_BAD_REQUEST)

        confirm_destructive = bool(data.get("confirm_destructive"))
        plan = plan_discard_person(person=person, confirm_destructive=confirm_destructive)
        if not plan.ok:
            payload = _build_delete_response(person=person, plan=plan)
            return Response(payload, status=status.HTTP_409_CONFLICT)

        before = _person_snapshot(person)
        actor = ctx.membership or request.user
        deleted_id = person.pk

        try:
            with transaction.atomic():
                audit_module.override_edit(
                    actor,
                    person,
                    before,
                    {"deleted": True},
                    reason=reason,
                    content_type="person_delete",
                    metadata={
                        "person_id": deleted_id,
                        "impact_counts": dict(plan.impact_counts),
                        "plan": serialize_discard_plan(plan),
                    },
                )
                discard_person(person=person, confirm_destructive=confirm_destructive)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        return Response({"ok": True, "person_id": deleted_id, "deleted": True})
