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


class RequestLineItemSerializer(serializers.Serializer):
    """A single requested item + quantity (camper-care or maintenance).

    ``item_id`` points at a :class:`CatalogItem` (the canonical label is
    re-derived server-side); ``item_label`` is the free-text fallback. At
    least one of the two must be present.
    """

    item_id = serializers.IntegerField(required=False, allow_null=True)
    item_label = serializers.CharField(
        max_length=120, required=False, allow_blank=True, default="",
    )
    quantity = serializers.IntegerField(min_value=1, default=1)
    note = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if not attrs.get("item_id") and not (attrs.get("item_label") or "").strip():
            msg = "Each line item needs item_id or item_label."
            raise serializers.ValidationError(msg)
        return attrs


class CamperCareRequestCreateSerializer(serializers.Serializer):
    """Counselor POST body for a Camper Care request (Story 7).

    Accepts either the legacy single ``item`` (free-text, with autocomplete
    against the catalog) or a structured ``line_items`` list with quantities.
    Both shapes are persisted as :class:`RequestLineItem` rows; ``Order.item``
    keeps a summary of the first line for back-compat with existing surfaces.
    The literal label is stored so admin edits to the catalog don't rewrite
    history. ``subject_id`` is the target camper; null when bunk-scoped.
    """

    subject_id = serializers.IntegerField(required=False, allow_null=True)
    bunk_id = serializers.IntegerField(required=False, allow_null=True)
    item = serializers.CharField(
        max_length=120, required=False, allow_blank=True, default="",
    )
    item_note = serializers.CharField(
        required=False, allow_blank=True, default="",
    )
    line_items = RequestLineItemSerializer(many=True, required=False)
    description = serializers.CharField(
        required=False, allow_blank=True, default="",
    )
    client_submission_id = serializers.UUIDField()

    def validate(self, attrs):
        has_item = bool((attrs.get("item") or "").strip())
        has_lines = bool(attrs.get("line_items"))
        if not has_item and not has_lines:
            msg = "Provide 'item' or at least one 'line_items' entry."
            raise serializers.ValidationError({"item": msg})
        return attrs


class CamperCareRequestUpdateSerializer(serializers.Serializer):
    """Counselor PATCH body for an open camper-care request they submitted."""

    subject_id = serializers.IntegerField(required=False, allow_null=True)
    bunk_id = serializers.IntegerField(required=False, allow_null=True)
    item = serializers.CharField(max_length=120, required=False)
    item_note = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if not attrs:
            msg = "At least one field must be provided."
            raise serializers.ValidationError(msg)
        return attrs


# ---------------------------------------------------------------------------
# Maintenance tickets
# ---------------------------------------------------------------------------


class MaintenanceTicketCreateSerializer(serializers.Serializer):
    """Counselor POST body for a Maintenance ticket (Story 8).

    ``category`` is now free-form text (max 120) validated by the view against
    the configurable catalog (active Maintenance-store items) plus the legacy
    ``MaintenanceTicket.Category`` enum values for back-compat. Optional
    ``line_items`` capture consumable supply requests with quantities. Photos
    are NOT validated here — multipart QueryDict + DRF's ListField don't
    compose cleanly, so the view reaches into ``request.FILES`` directly.
    ``urgent_reason`` is enforced by ``MaintenanceTicket.clean()`` when
    urgency = ``urgent``.
    """

    location = serializers.CharField(max_length=255)
    category = serializers.CharField(max_length=120)
    line_items = RequestLineItemSerializer(many=True, required=False)
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
