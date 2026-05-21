"""Write-side serializers for Unit Head endpoints (Step 7_7).

UH self-reflection serializers mirror their counselor counterparts in
shape; the view layer adds UH-specific authorization (active
``unit_head`` Membership) and ``bunk_concerns_bunks`` validation
against the viewer's supervised bunks.
"""

from __future__ import annotations

from rest_framework import serializers


class UnitHeadSelfReflectionCreateSerializer(serializers.Serializer):
    """UH POST body for daily self-reflection (Story 16).

    Mirrors the counselor self-reflection serializer including the
    ``day_off`` shortcut. The optional ``bunk_concerns_bunks`` payload
    lives inside ``answers`` (no top-level field) and is enforced by
    the view against the viewer's supervised bunk IDs.
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


class UnitHeadSelfReflectionUpdateSerializer(serializers.Serializer):
    """UH PATCH body within today's edit window (Story 17 criterion 2)."""

    answers = serializers.JSONField(required=False)
    day_off = serializers.BooleanField(required=False)
    language = serializers.CharField(max_length=10, required=False)

    def validate(self, attrs):
        if not attrs:
            msg = "At least one field must be provided."
            raise serializers.ValidationError(msg)
        return attrs
