"""Faculty Classroom Challenge Log endpoints — Step 4_8, MA7.

Endpoints
---------
GET   /api/v1/faculty/challenges/                -- classrooms the viewer authors
GET   /api/v1/faculty/challenges/<id>/            -- full detail (author identity visible)
PATCH /api/v1/faculty/challenges/<id>/            -- update status (acknowledged/resolved)
POST  /api/v1/faculty/challenges/<id>/responses/  -- reply

Faculty always see the author's identity (semi-anonymity is peer-Madrich
only, see ``api.classroom_challenges.common``). The first faculty reply
auto-transitions an ``open`` challenge to ``acknowledged``.
"""

from __future__ import annotations

from django.db.models import Count
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import serializers
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.api.classroom_challenges.common import challenge_detail
from bunk_logs.api.classroom_challenges.common import challenge_list_item
from bunk_logs.api.classroom_challenges.common import classroom_group_ids_for_role
from bunk_logs.core import audit as audit_module
from bunk_logs.core.models import ClassroomChallenge
from bunk_logs.core.models import ClassroomChallengeResponse

from .common import ViewerContext
from .common import viewer_or_403


class ClassroomChallengeResponseCreateSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=2000)

    def validate_body(self, value: str) -> str:
        value = value.strip()
        if not value:
            msg = "Body is required."
            raise serializers.ValidationError(msg)
        return value


class ClassroomChallengeStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[ClassroomChallenge.STATUS_ACKNOWLEDGED, ClassroomChallenge.STATUS_RESOLVED],
    )


def _authored_classroom_ids(ctx: ViewerContext) -> list[int]:
    return classroom_group_ids_for_role(ctx.person, ctx.program, role_in_group="author")


def _detail_or_404(challenge_id) -> ClassroomChallenge:
    challenge = (
        ClassroomChallenge.objects.filter(id=challenge_id)
        .select_related("author", "assignment_group", "resolved_by")
        .prefetch_related("responses__author")
        .first()
    )
    if challenge is None:
        msg = "Challenge not found."
        raise NotFound(msg)
    return challenge


def _authorize(ctx: ViewerContext, challenge: ClassroomChallenge) -> None:
    if challenge.assignment_group_id not in _authored_classroom_ids(ctx):
        msg = "You do not have access to this challenge."
        raise PermissionDenied(msg)


class FacultyChallengeListView(APIView):
    """``GET .../faculty/challenges/`` -- challenges in classrooms the viewer authors."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "head", "options"]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        classroom_ids = _authored_classroom_ids(ctx)
        if not classroom_ids:
            return Response({"results": []})

        qs = ClassroomChallenge.objects.filter(assignment_group_id__in=classroom_ids)

        classroom_param = request.query_params.get("classroom")
        if classroom_param:
            try:
                classroom_id = int(classroom_param)
            except (TypeError, ValueError) as exc:
                msg = "Invalid 'classroom' parameter."
                raise ValidationError(msg) from exc
            if classroom_id not in classroom_ids:
                msg = "You do not have access to this classroom."
                raise PermissionDenied(msg)
            qs = qs.filter(assignment_group_id=classroom_id)

        status_param = request.query_params.get("status")
        if status_param:
            if status_param not in dict(ClassroomChallenge.STATUS_CHOICES):
                msg = "Invalid 'status' parameter."
                raise ValidationError(msg)
            qs = qs.filter(status=status_param)

        session_date_param = request.query_params.get("session_date")
        if session_date_param:
            parsed = parse_date(session_date_param)
            if parsed is None:
                msg = "Invalid 'session_date' parameter; expected YYYY-MM-DD."
                raise ValidationError(msg)
            qs = qs.filter(session_date=parsed)

        # Meta.ordering already sorts -created_at; stable-sort open first.
        rows = sorted(
            qs.select_related("author", "assignment_group").annotate(response_count=Count("responses")),
            key=lambda c: c.status != ClassroomChallenge.STATUS_OPEN,
        )
        results = [
            challenge_list_item(c, redacted=False, response_count=c.response_count, include_group=True)
            for c in rows
        ]
        return Response({"results": results})


class FacultyChallengeDetailView(APIView):
    """``GET``/``PATCH .../faculty/challenges/<id>/``."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get(self, request, challenge_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        challenge = _detail_or_404(challenge_id)
        _authorize(ctx, challenge)
        return Response(challenge_detail(challenge, redacted=False))

    def patch(self, request, challenge_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        challenge = _detail_or_404(challenge_id)
        _authorize(ctx, challenge)

        ser = ClassroomChallengeStatusUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        new_status = ser.validated_data["status"]

        before_status = challenge.status
        if before_status != new_status:
            challenge.status = new_status
            if new_status == ClassroomChallenge.STATUS_RESOLVED:
                challenge.resolved_at = timezone.now()
                challenge.resolved_by = ctx.person
            challenge.full_clean()
            challenge.save()
            audit_module.state_changed(
                ctx.membership, challenge,
                before_state=before_status, after_state=new_status,
                content_type="classroom_challenge",
            )
        return Response(challenge_detail(challenge, redacted=False))


class FacultyChallengeResponseCreateView(APIView):
    """``POST .../faculty/challenges/<id>/responses/`` -- reply."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["post", "head", "options"]

    def post(self, request, challenge_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        challenge = ClassroomChallenge.objects.filter(id=challenge_id).first()
        if challenge is None:
            msg = "Challenge not found."
            raise NotFound(msg)
        _authorize(ctx, challenge)

        ser = ClassroomChallengeResponseCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        response = ClassroomChallengeResponse(
            challenge=challenge, author=ctx.person, body=ser.validated_data["body"],
        )
        response.full_clean()
        response.save()
        audit_module.created(
            ctx.membership, response,
            after_state={"body": response.body},
            content_type="classroom_challenge_response",
        )

        if challenge.status == ClassroomChallenge.STATUS_OPEN:
            before_status = challenge.status
            challenge.status = ClassroomChallenge.STATUS_ACKNOWLEDGED
            challenge.save(update_fields=["status", "updated_at"])
            audit_module.state_changed(
                ctx.membership, challenge,
                before_state=before_status, after_state=challenge.status,
                content_type="classroom_challenge",
            )

        challenge = _detail_or_404(challenge.id)
        return Response(challenge_detail(challenge, redacted=False), status=status.HTTP_201_CREATED)
