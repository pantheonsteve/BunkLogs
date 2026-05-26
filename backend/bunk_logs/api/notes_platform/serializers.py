"""Serializers for the Notes platform API (Step 7_19)."""

from __future__ import annotations

from rest_framework import serializers

from bunk_logs.notes.models import Note
from bunk_logs.notes.models import NoteAudienceCapture
from bunk_logs.notes.models import NoteReply


class PersonSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField()


class NoteReplySerializer(serializers.ModelSerializer):
    author = PersonSummarySerializer(read_only=True)

    class Meta:
        model = NoteReply
        fields = ["id", "author", "author_role_at_write", "body", "created_at"]


class NoteListSerializer(serializers.ModelSerializer):
    """Compact serializer for list endpoints (Inbox, Sent, Archive)."""

    author = PersonSummarySerializer(read_only=True)
    last_activity_at = serializers.SerializerMethodField()
    unread = serializers.SerializerMethodField()
    audience_summary = serializers.SerializerMethodField()

    class Meta:
        model = Note
        fields = [
            "id",
            "subject",
            "author",
            "created_at",
            "last_activity_at",
            "unread",
            "audience_summary",
            "camper_reference_id",
        ]

    def get_last_activity_at(self, note: Note) -> str:
        last_reply = note.replies.order_by("-created_at").first()
        if last_reply:
            return last_reply.created_at.isoformat()
        return note.created_at.isoformat()

    def get_unread(self, note: Note) -> bool:
        request = self.context.get("request")
        if request is None:
            return False
        person = getattr(request, "_notes_person", None)
        if person is None:
            return False
        receipt = note.read_receipts.filter(person=person).first()
        if receipt is None:
            # Never read — note itself is unread
            return True
        # Check if there's activity after the last read time
        last_reply = note.replies.order_by("-created_at").first()
        latest = last_reply.created_at if last_reply else note.created_at
        return latest > receipt.last_read_at

    def get_audience_summary(self, note: Note) -> str:
        captures = note.audience_captures.select_related("person")[:3]
        names = [c.person.full_name for c in captures]
        total = note.audience_captures.count()
        if total > 3:
            return f"{', '.join(names)} +{total - 3} more"
        return ", ".join(names)


class AudienceCaptureSerializer(serializers.ModelSerializer):
    person = PersonSummarySerializer(read_only=True)

    class Meta:
        model = NoteAudienceCapture
        fields = ["person", "option_key"]


class NoteThreadSerializer(serializers.ModelSerializer):
    """Full thread serializer including replies and read receipt counts."""

    author = PersonSummarySerializer(read_only=True)
    replies = NoteReplySerializer(many=True, read_only=True)
    audience = AudienceCaptureSerializer(many=True, source="audience_captures", read_only=True)
    read_summary = serializers.SerializerMethodField()
    camper_reference_id = serializers.IntegerField(allow_null=True, required=False)

    class Meta:
        model = Note
        fields = [
            "id",
            "subject",
            "body",
            "author",
            "author_role_at_write",
            "created_at",
            "camper_reference_id",
            "source_content_type",
            "source_object_id",
            "audience",
            "replies",
            "read_summary",
        ]

    def get_read_summary(self, note: Note) -> dict:
        audience_count = note.audience_captures.count()
        read_count = note.read_receipts.count()
        return {"read_count": read_count, "audience_count": audience_count}


class AudienceOptionSerializer(serializers.Serializer):
    option_key = serializers.CharField()
    label = serializers.CharField()


class NoteCreateSerializer(serializers.Serializer):
    """Deserializer for POST /api/v1/notes/."""

    audience = serializers.ListField(child=serializers.DictField(), min_length=1)
    subject = serializers.CharField(max_length=200)
    body = serializers.CharField(max_length=10000)
    camper_reference_id = serializers.IntegerField(required=False, allow_null=True)
    source_content_type = serializers.ChoiceField(
        choices=["", "reflection_concern", "specialist_note"],
        required=False,
        default="",
    )
    source_object_id = serializers.CharField(max_length=50, required=False, default="")


class NoteReplyCreateSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=10000)


class UnreadCountSerializer(serializers.Serializer):
    count = serializers.IntegerField()
