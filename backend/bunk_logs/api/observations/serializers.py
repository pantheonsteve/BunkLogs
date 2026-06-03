"""Serializers for the Observations API (Step 7_23)."""

from __future__ import annotations

from rest_framework import serializers

from bunk_logs.notes.models import Observation
from bunk_logs.notes.models import ObservationReply


class PersonSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField()


class ObservationReplySerializer(serializers.ModelSerializer):
    author = PersonSummarySerializer(read_only=True)

    class Meta:
        model = ObservationReply
        fields = ["id", "author", "author_role_at_write", "body", "created_at"]


class ObservationListSerializer(serializers.ModelSerializer):
    """Compact serializer for the inbox list."""

    author = PersonSummarySerializer(read_only=True)
    last_activity_at = serializers.SerializerMethodField()
    unread = serializers.SerializerMethodField()
    subjects_summary = serializers.SerializerMethodField()
    viewer_is_author = serializers.SerializerMethodField()

    class Meta:
        model = Observation
        fields = [
            "id",
            "author",
            "context",
            "sensitivity",
            "observed_at",
            "created_at",
            "last_activity_at",
            "unread",
            "subjects_summary",
            "viewer_is_author",
        ]

    def _person(self):
        request = self.context.get("request")
        return getattr(request, "_notes_person", None) if request else None

    def get_viewer_is_author(self, obs: Observation) -> bool:
        person = self._person()
        return bool(person and obs.author_id == person.id)

    def get_last_activity_at(self, obs: Observation) -> str:
        last_reply = obs.replies.order_by("-created_at").first()
        if last_reply:
            return last_reply.created_at.isoformat()
        return obs.created_at.isoformat()

    def get_unread(self, obs: Observation) -> bool:
        from .views import has_unread_activity
        person = self._person()
        if person is None:
            return False
        return has_unread_activity(obs, person, is_author=obs.author_id == person.id)

    def get_subjects_summary(self, obs: Observation) -> str:
        names = [link.subject.full_name for link in obs.subject_links.all()[:3]]
        total = obs.subject_links.count()
        if total > 3:
            return f"{', '.join(names)} +{total - 3} more"
        return ", ".join(names)


class ObservationSubjectSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField(source="subject_id")
    full_name = serializers.CharField(source="subject.full_name")


class ObservationRecipientSerializer(serializers.Serializer):
    person = PersonSummarySerializer(read_only=True)
    option_key = serializers.CharField()


class ObservationThreadSerializer(serializers.ModelSerializer):
    author = PersonSummarySerializer(read_only=True)
    replies = ObservationReplySerializer(many=True, read_only=True)
    subjects = serializers.SerializerMethodField()
    recipients = serializers.SerializerMethodField()
    read_summary = serializers.SerializerMethodField()

    class Meta:
        model = Observation
        fields = [
            "id",
            "body",
            "author",
            "author_role_at_write",
            "context",
            "sensitivity",
            "subject_visible",
            "language",
            "amendment_of",
            "source_content_type",
            "source_object_id",
            "observed_at",
            "created_at",
            "subjects",
            "recipients",
            "replies",
            "read_summary",
        ]

    def get_subjects(self, obs: Observation) -> list[dict]:
        return [
            {"id": link.subject_id, "full_name": link.subject.full_name}
            for link in obs.subject_links.select_related("subject").all()
        ]

    def get_recipients(self, obs: Observation) -> list[dict]:
        return [
            {"person": {"id": r.person_id, "full_name": r.person.full_name}, "option_key": r.option_key}
            for r in obs.recipients.select_related("person").all()
        ]

    def get_read_summary(self, obs: Observation) -> dict:
        return {
            "read_count": obs.read_receipts.count(),
            "audience_count": obs.recipients.count(),
        }


class ObservationCreateSerializer(serializers.Serializer):
    subject_ids = serializers.ListField(child=serializers.IntegerField(), min_length=1)
    recipient_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, default=list,
    )
    body = serializers.CharField(max_length=10000)
    context = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")
    sensitivity = serializers.ChoiceField(
        choices=Observation.Sensitivity.values,
        required=False,
        default=Observation.Sensitivity.NORMAL,
    )
    subject_visible = serializers.BooleanField(required=False, default=False)
    source_content_type = serializers.CharField(
        max_length=32, required=False, allow_blank=True, default="",
    )
    source_object_id = serializers.CharField(
        max_length=50, required=False, allow_blank=True, default="",
    )
    observed_at = serializers.DateTimeField(required=False, allow_null=True)


class ObservationReplyCreateSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=10000)


class ObservationAmendSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=10000)
