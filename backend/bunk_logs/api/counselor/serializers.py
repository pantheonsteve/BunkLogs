"""Write-side serializers for the counselor flow (Step 7_6c).

Each serializer here is intentionally a flat ``serializers.Serializer`` (not
``ModelSerializer``) so the views can hand-shape the create / update logic
without the field locking that ``ReflectionSerializer`` ships for the
admin-facing path. The views own: subject + bunk authorization, template
resolution, idempotency, audit emission, and cache invalidation. These
serializers own: field types, required-ness, and per-field shape validation.

Response shaping lives in :mod:`bunk_logs.api.counselor.responses` so list
endpoints, create responses, and patch responses agree on the same camper /
counselor / template payload.
"""

from __future__ import annotations

from rest_framework import serializers

from bunk_logs.core.models import MaintenanceTicket
from bunk_logs.core.models import Reflection

# ---------------------------------------------------------------------------
# Reflections
# ---------------------------------------------------------------------------


class CamperReflectionCreateSerializer(serializers.Serializer):
    """Counselor POST body for a single camper reflection.

    The bunk is provided as ``assignment_group_id`` (canonical) with
    ``bunk_id`` accepted as an alias to match the client form schema. The
    template is **not** client-supplied — the view resolves it via
    ``camper_reflection_template`` so a misconfigured client can't submit
    against the wrong schema.
    """

    subject_id = serializers.IntegerField()
    assignment_group_id = serializers.IntegerField(required=False)
    bunk_id = serializers.IntegerField(required=False, write_only=True)
    answers = serializers.JSONField()
    language = serializers.CharField(max_length=10, default="en")
    team_visibility = serializers.ChoiceField(
        choices=Reflection.TeamVisibility.choices,
        default=Reflection.TeamVisibility.TEAM,
    )
    client_submission_id = serializers.UUIDField()

    def validate(self, attrs):
        ag = attrs.get("assignment_group_id") or attrs.get("bunk_id")
        if not ag:
            msg = "assignment_group_id (or bunk_id) is required."
            raise serializers.ValidationError({"assignment_group_id": msg})
        attrs["assignment_group_id"] = ag
        attrs.pop("bunk_id", None)
        return attrs


class CamperReflectionUpdateSerializer(serializers.Serializer):
    """Counselor PATCH body for an existing camper reflection.

    Only the mutable fields are editable; ``subject``, ``assignment_group``,
    ``template``, and ``period_*`` are locked once the row exists. ``answers``
    and ``language`` are independently optional so a counselor can fix a
    typo without re-sending the entire payload.
    """

    answers = serializers.JSONField(required=False)
    language = serializers.CharField(max_length=10, required=False)
    team_visibility = serializers.ChoiceField(
        choices=Reflection.TeamVisibility.choices,
        required=False,
    )

    def validate(self, attrs):
        if not attrs:
            msg = "At least one field must be provided."
            raise serializers.ValidationError(msg)
        return attrs


class SelfReflectionCreateSerializer(serializers.Serializer):
    """Counselor POST body for daily self-reflection.

    ``day_off`` is a UX shortcut: when true the view fills ``answers`` with
    ``{"day_off": true}`` regardless of what the client sends, so the offline
    queue doesn't need to know the full schema to record a day off. When
    false the client is responsible for sending a complete ``answers`` payload
    that satisfies the seeded counselor self-reflection schema.
    """

    answers = serializers.JSONField(required=False)
    day_off = serializers.BooleanField(default=False)
    language = serializers.CharField(max_length=10, default="en")
    client_submission_id = serializers.UUIDField()

    def validate(self, attrs):
        if not attrs.get("day_off") and not attrs.get("answers"):
            msg = "answers is required unless day_off is true."
            raise serializers.ValidationError({"answers": msg})
        return attrs


class SelfReflectionUpdateSerializer(serializers.Serializer):
    """Counselor PATCH body for self-reflection within the edit window."""

    answers = serializers.JSONField(required=False)
    day_off = serializers.BooleanField(required=False)
    language = serializers.CharField(max_length=10, required=False)

    def validate(self, attrs):
        if not attrs:
            msg = "At least one field must be provided."
            raise serializers.ValidationError(msg)
        return attrs


# ---------------------------------------------------------------------------
# Camper-care requests (Order)
# ---------------------------------------------------------------------------


class CamperCareRequestCreateSerializer(serializers.Serializer):
    """Counselor POST body for a Camper Care request (Story 7).

    ``item`` is free-text but the client surfaces an autocomplete from
    :class:`OrderItemSuggestion`. We store the literal label so admin edits
    to the suggestion list don't rewrite history. ``subject_id`` is the
    target camper Person; null when the request is bunk-scoped (rare).
    """

    subject_id = serializers.IntegerField(required=False, allow_null=True)
    bunk_id = serializers.IntegerField(required=False, allow_null=True)
    item = serializers.CharField(max_length=120)
    item_note = serializers.CharField(
        required=False, allow_blank=True, default="",
    )
    description = serializers.CharField(
        required=False, allow_blank=True, default="",
    )
    client_submission_id = serializers.UUIDField()


# ---------------------------------------------------------------------------
# Maintenance tickets
# ---------------------------------------------------------------------------


class MaintenanceTicketCreateSerializer(serializers.Serializer):
    """Counselor POST body for a Maintenance ticket (Story 8).

    Photos are NOT validated here — multipart QueryDict + DRF's ListField
    don't compose cleanly (the field collapses repeated keys to a single
    value), so the view reaches into ``request.FILES`` directly to collect
    the upload list and validate each item individually. ``urgent_reason``
    is enforced by ``MaintenanceTicket.clean()`` when urgency = ``urgent``.
    """

    location = serializers.CharField(max_length=255)
    category = serializers.ChoiceField(
        choices=MaintenanceTicket.Category.choices,
    )
    description = serializers.CharField(allow_blank=True, default="")
    urgency = serializers.ChoiceField(
        choices=MaintenanceTicket.Urgency.choices,
        default=MaintenanceTicket.Urgency.NORMAL,
    )
    urgent_reason = serializers.CharField(
        required=False, allow_blank=True, default="",
    )
    client_submission_id = serializers.UUIDField()


class MaintenanceTicketPhotoUploadSerializer(serializers.Serializer):
    """Follow-up photo upload (decision C5).

    Counselors can add additional photos to their own open tickets after the
    initial submission. The view marks these with ``is_followup=True`` so
    the maintenance team UI can render them in chronological context under
    the original submission.
    """

    image = serializers.ImageField()
    caption = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default="",
    )
