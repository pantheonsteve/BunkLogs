"""DRF serializers for LT write endpoints."""

from __future__ import annotations

from rest_framework import serializers


class LTSelfReflectionCreateSerializer(serializers.Serializer):
    answers = serializers.JSONField(required=False)
    language = serializers.CharField(max_length=10, default="en")
    is_private = serializers.BooleanField(default=False)
    client_submission_id = serializers.UUIDField()

    def validate(self, attrs):
        if not attrs.get("answers"):
            msg = {"answers": "answers is required."}
            raise serializers.ValidationError(msg)
        return attrs


class LTSelfReflectionUpdateSerializer(serializers.Serializer):
    answers = serializers.JSONField(required=False)
    language = serializers.CharField(max_length=10, required=False)
    is_private = serializers.BooleanField(required=False)

    def validate(self, attrs):
        if not attrs:
            msg = "At least one field must be provided."
            raise serializers.ValidationError(msg)
        return attrs
