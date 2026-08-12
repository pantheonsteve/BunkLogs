"""Madrich Classroom Challenge Log endpoints — Step 4_8, MA7.

Endpoints
---------
GET  /api/v1/madrich/challenges/classrooms/     -- classrooms the viewer is a subject of
GET  /api/v1/madrich/challenges/                -- peer-safe list (or ``?mine=1``)
POST /api/v1/madrich/challenges/                -- submit a challenge
GET  /api/v1/madrich/challenges/<id>/           -- detail with responses
POST /api/v1/madrich/challenges/<id>/close/     -- withdraw (author, no responses yet)

Semi-anonymity (MA7): a peer Madrich sees *that* a challenge was raised
(category, timestamp, body) but never the author; the author always
sees their own name. Faculty replies stay attributed regardless of
viewer -- see ``api.classroom_challenges.common``.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count
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
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import ClassroomChallenge
from bunk_logs.core.scheduling.sessions import program_session_dates

from .common import viewer_or_403

if TYPE_CHECKING:
    from datetime import date as date_type

    from bunk_logs.core.models import Program


def _next_session_date(program: Program, today: date_type) -> date_type:
    """First configured session on/after ``today``, else the next Sunday."""
    upcoming = [d for d in program_session_dates(program) if d >= today]
    if upcoming:
        return upcoming[0]
    days_ahead = (6 - today.weekday()) % 7
    return today + timedelta(days=days_ahead)


class ClassroomChallengeCreateSerializer(serializers.Serializer):
    assignment_group_id = serializers.IntegerField()
    session_date = serializers.DateField(required=False)
    category = serializers.ChoiceField(choices=ClassroomChallenge.CATEGORY_CHOICES)
    body = serializers.CharField(max_length=2000)

    def validate_body(self, value: str) -> str:
        value = value.strip()
        if not value:
            msg = "Body is required."
            raise serializers.ValidationError(msg)
        return value


class MadrichChallengeClassroomsView(APIView):
    """``GET .../madrich/challenges/classrooms/`` -- classrooms the viewer can report into."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "head", "options"]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        group_ids = classroom_group_ids_for_role(ctx.person, ctx.program, role_in_group="subject")
        groups = AssignmentGroup.objects.filter(id__in=group_ids, is_active=True).order_by("name")
        default_session = _next_session_date(ctx.program, ctx.today).isoformat()
        return Response({
            "classrooms": [
                {
                    "assignment_group_id": g.id,
                    "name": g.name,
                    "session_date_default": default_session,
                }
                for g in groups
            ],
        })


class MadrichChallengeListCreateView(APIView):
    """``GET``/``POST .../madrich/challenges/``."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        classroom_ids = classroom_group_ids_for_role(ctx.person, ctx.program, role_in_group="subject")
        mine = request.query_params.get("mine") == "1"

        if mine:
            qs = ClassroomChallenge.objects.filter(author=ctx.person)
        elif not classroom_ids:
            return Response({"results": []})
        else:
            qs = ClassroomChallenge.objects.filter(assignment_group_id__in=classroom_ids)

        classroom_param = request.query_params.get("classroom")
        if classroom_param:
            try:
                classroom_id = int(classroom_param)
            except (TypeError, ValueError) as exc:
                msg = "Invalid 'classroom' parameter."
                raise ValidationError(msg) from exc
            if not mine and classroom_id not in classroom_ids:
                msg = "You do not have access to this classroom."
                raise PermissionDenied(msg)
            qs = qs.filter(assignment_group_id=classroom_id)

        session_date_param = request.query_params.get("session_date")
        if session_date_param:
            parsed = parse_date(session_date_param)
            if parsed is None:
                msg = "Invalid 'session_date' parameter; expected YYYY-MM-DD."
                raise ValidationError(msg)
            qs = qs.filter(session_date=parsed)

        qs = qs.select_related("author").annotate(response_count=Count("responses"))
        results = [
            challenge_list_item(
                c, redacted=(c.author_id != ctx.person.id), response_count=c.response_count,
            )
            for c in qs
        ]
        return Response({"results": results})

    def post(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        ser = ClassroomChallengeCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        payload = ser.validated_data

        group_id = payload["assignment_group_id"]
        classroom_ids = classroom_group_ids_for_role(ctx.person, ctx.program, role_in_group="subject")
        if group_id not in classroom_ids:
            msg = "You are not a member of this classroom."
            raise PermissionDenied(msg)
        group = AssignmentGroup.objects.filter(id=group_id, group_type="classroom").first()
        if group is None:
            msg = "You are not a member of this classroom."
            raise PermissionDenied(msg)

        session_date = payload.get("session_date") or _next_session_date(ctx.program, ctx.today)

        challenge = ClassroomChallenge(
            organization=ctx.organization,
            program=ctx.program,
            assignment_group=group,
            author=ctx.person,
            session_date=session_date,
            category=payload["category"],
            body=payload["body"],
        )
        try:
            challenge.full_clean()
        except DjangoValidationError as exc:
            body = exc.message_dict if hasattr(exc, "message_dict") else {"detail": str(exc)}
            return Response(body, status=status.HTTP_400_BAD_REQUEST)
        challenge.save()

        audit_module.created(
            ctx.membership, challenge,
            after_state={"category": challenge.category, "status": challenge.status},
            content_type="classroom_challenge",
        )
        return Response(challenge_detail(challenge, redacted=False), status=status.HTTP_201_CREATED)


class MadrichChallengeDetailView(APIView):
    """``GET .../madrich/challenges/<id>/`` -- detail with responses."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "head", "options"]

    def get(self, request, challenge_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        challenge = (
            ClassroomChallenge.objects.filter(id=challenge_id)
            .select_related("author", "assignment_group", "resolved_by")
            .prefetch_related("responses__author")
            .first()
        )
        if challenge is None:
            msg = "Challenge not found."
            raise NotFound(msg)
        is_author = challenge.author_id == ctx.person.id
        if not is_author:
            classroom_ids = classroom_group_ids_for_role(ctx.person, ctx.program, role_in_group="subject")
            if challenge.assignment_group_id not in classroom_ids:
                msg = "You do not have access to this challenge."
                raise PermissionDenied(msg)
        return Response(challenge_detail(challenge, redacted=not is_author))


class MadrichChallengeCloseView(APIView):
    """``POST .../madrich/challenges/<id>/close/`` -- withdraw own report."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["post", "head", "options"]

    def post(self, request, challenge_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        challenge = ClassroomChallenge.objects.filter(id=challenge_id).first()
        if challenge is None:
            msg = "Challenge not found."
            raise NotFound(msg)
        if challenge.author_id != ctx.person.id:
            msg = "You can only withdraw your own challenge."
            raise PermissionDenied(msg)
        if challenge.responses.exists():
            msg = "This challenge already has a faculty response and can no longer be withdrawn."
            raise PermissionDenied(msg)

        audit_module.state_changed(
            ctx.membership, challenge,
            before_state=challenge.status, after_state="withdrawn",
            content_type="classroom_challenge",
        )
        challenge.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
