"""Write-side serializers for Camper Care endpoints (Step 7_8).

CC self-reflection serializers mirror UH's shape — view layer adds
CC-specific authorization (active ``camper_care`` Membership) and
``bunk_concerns_bunks`` validation against the viewer's caseload.
"""

from __future__ import annotations

from rest_framework import serializers


class CamperCareSelfReflectionCreateSerializer(serializers.Serializer):
    """CC POST body for daily self-reflection (Story 18 c.10 / Story 16 analog)."""

    answers = serializers.JSONField(required=False)
    day_off = serializers.BooleanField(default=False)
    language = serializers.CharField(max_length=10, default="en")
    client_submission_id = serializers.UUIDField()

    def validate(self, attrs):
        if not attrs.get("day_off") and not attrs.get("answers"):
            msg = "answers is required unless day_off is true."
            raise serializers.ValidationError({"answers": msg})
        return attrs


class CamperCareSelfReflectionUpdateSerializer(serializers.Serializer):
    """CC PATCH body within today's edit window."""

    answers = serializers.JSONField(required=False)
    day_off = serializers.BooleanField(required=False)
    language = serializers.CharField(max_length=10, required=False)

    def validate(self, attrs):
        if not attrs:
            msg = "At least one field must be provided."
            raise serializers.ValidationError(msg)
        return attrs
