"""``POST /api/v1/leadership-team/reflections/<id>/mark-attention/`` — Story 46 c5.

Places a :class:`ReflectionAttentionMarker` on a reflection authored by
a team member the LT viewer supervises. The marker is visible to the
viewer and to co-supervisors (Supervisions sharing the same
``ROLE_IN_PROGRAM`` target), but does NOT mutate the reflection or
notify the author.

A subsequent POST by the same marker_membership is idempotent — we
``update_or_create`` keyed on ``(reflection, marker_membership)`` so
repeated taps don't pile up duplicate rows. The optional ``note``
captures the supervisor's reason and replaces the previous note when
re-marking.

DELETE removes the viewer's own marker (un-mark). DELETE by other
supervisors is rejected with 403 so one LT cannot quietly suppress a
peer's attention flag.
"""

from __future__ import annotations

from rest_framework import serializers
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core import audit as audit_module
from bunk_logs.core.filters import reflections_visible_for_user
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionAttentionMarker

from .common import viewer_or_403


class _MarkAttentionSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)


class LeadershipTeamMarkAttentionView(APIView):
    """Mark / unmark a reflection as needing attention."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["post", "delete", "head", "options"]

    def post(self, request, reflection_id: int, *args, **kwargs):
        ctx = viewer_or_403(request)
        reflection = _get_visible_reflection(request, ctx, reflection_id)

        ser = _MarkAttentionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        note = (ser.validated_data.get("note") or "").strip()

        marker, created = ReflectionAttentionMarker.all_objects.update_or_create(
            reflection=reflection,
            marker_membership=ctx.membership,
            defaults={
                "organization": ctx.organization,
                "note": note,
            },
        )
        audit_module.created(
            ctx.membership, marker,
            after_state={
                "reflection_id": reflection.id,
                "note": note,
            },
            content_type="reflection_attention_marker",
        )
        return Response({
            "id": marker.id,
            "reflection_id": reflection.id,
            "marker_membership_id": ctx.membership.id,
            "note": marker.note,
            "created": created,
            "created_at": marker.created_at.isoformat(),
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    def delete(self, request, reflection_id: int, *args, **kwargs):
        ctx = viewer_or_403(request)
        reflection = _get_visible_reflection(request, ctx, reflection_id)

        marker = ReflectionAttentionMarker.all_objects.filter(
            reflection=reflection, marker_membership=ctx.membership,
        ).first()
        if marker is None:
            msg = "No attention marker to remove."
            raise NotFound(msg)
        before = {"reflection_id": reflection.id, "note": marker.note}
        marker.delete()
        audit_module.deactivated(
            ctx.membership, reflection,
            before_state=before,
            content_type="reflection_attention_marker",
            reason="attention marker removed",
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


def _get_visible_reflection(request, ctx, reflection_id: int) -> Reflection:
    """Resolve a reflection the LT viewer is allowed to flag.

    Visibility uses the standard ``RoleVisibilityFilterBackend`` query
    so we don't accidentally widen the audience by relying on
    supervision alone. A reflection the LT cannot read cannot be
    flagged either.
    """
    reflection = (
        Reflection.all_objects.filter(id=reflection_id, organization=ctx.organization)
        .select_related("template", "author", "program")
        .first()
    )
    if reflection is None:
        msg = "Reflection not found."
        raise NotFound(msg)
    visible = reflections_visible_for_user(
        request.user,
        Reflection.all_objects.filter(id=reflection_id),
    )
    if not visible.exists():
        msg = "You may not flag this reflection."
        raise PermissionDenied(msg)
    return reflection
