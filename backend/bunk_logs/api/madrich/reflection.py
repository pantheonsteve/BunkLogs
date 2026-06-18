"""Madrich self-reflection endpoints — Stories 62, 64, 65.

Endpoints
---------
POST  /api/v1/madrich/reflection/             — submit weekly reflection (Story 62)
PATCH /api/v1/madrich/reflection/<id>/        — edit while week is open (Story 62 c5-6)
GET   /api/v1/madrich/reflection/history/     — paginated weekly history (Story 65)

Key invariants
--------------
* Period is Monday-Sunday per MA1 (overridable per program). Both
  ``period_start`` and ``period_end`` come from ``current_week_period``
  so create and edit converge on the same window.
* No day-off shortcut per Story 62 criterion 3 — payloads always carry
  full 3-2-1 answers and the template schema enforces exact counts via
  ``min_items``/``max_items``.
* Edit window: ``period_start <= today <= period_end``; once the week
  closes the row is read-only per Story 62 criterion 6.
* History returns one row per past week back through the program start
  (or a bounded window when the start date is absent), with "gap" rows
  for weeks the Madrich did not submit per Story 65 criterion 4.
"""

from __future__ import annotations

from datetime import date as date_type
from datetime import timedelta

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.api.counselor.common import invalidate_dashboard_for_viewers
from bunk_logs.api.counselor.responses import reflection_response
from bunk_logs.core import audit as audit_module
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import reflection_snapshot
from bunk_logs.core.models import validate_reflection_answers
from bunk_logs.core.submission import idempotent_create

from .common import current_week_period
from .common import enforce_period_edit_window
from .common import madrich_template
from .common import viewer_or_403


class MadrichReflectionCreateSerializer(serializers.Serializer):
    answers = serializers.JSONField()
    language = serializers.CharField(max_length=10, default="en")
    client_submission_id = serializers.UUIDField()


class MadrichReflectionUpdateSerializer(serializers.Serializer):
    answers = serializers.JSONField(required=False)
    language = serializers.CharField(max_length=10, required=False)

    def validate(self, attrs):
        if not attrs:
            msg = "At least one field must be provided."
            raise serializers.ValidationError(msg)
        return attrs


class MadrichReflectionHistoryPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = "page_size"
    max_page_size = 52


def _preview_from_answers(answers: dict | None, max_len: int = 120) -> str:
    """Story 65 c2: first line of "1 question or concern" (preferred) or fallback."""
    if not answers:
        return ""
    preferred = answers.get("question_or_concern")
    if isinstance(preferred, str) and preferred.strip():
        text = preferred.strip()
        return text if len(text) <= max_len else text[: max_len - 1] + "\u2026"
    for value in answers.values():
        if isinstance(value, str) and value.strip():
            text = value.strip()
            return text if len(text) <= max_len else text[: max_len - 1] + "\u2026"
    return ""


def _validate_answers(template, answers: dict) -> tuple[bool, Response | None]:
    try:
        validate_reflection_answers(template.schema, answers)
    except DjangoValidationError as exc:
        body = exc.message_dict if hasattr(exc, "message_dict") else {"answers": str(exc)}
        return False, Response(body, status=status.HTTP_400_BAD_REQUEST)
    return True, None


class MadrichReflectionHistoryView(APIView):
    """Paginated weekly reflection history for the authenticated Madrich.

    Each row represents one week back from "today's" current week. Weeks
    with no submission appear as gap rows per Story 65 c4. The window is
    bounded by the program's ``start_date`` when present, otherwise by
    ``max_page_size * page_size`` weeks back.
    """

    permission_classes = [IsAuthenticated]
    pagination_class = MadrichReflectionHistoryPagination

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        viewer, org = ctx.person, ctx.organization
        today = ctx.today

        template = madrich_template(org, ctx.program)
        paginator = self.pagination_class()
        page_size = paginator.get_page_size(request) or paginator.page_size
        try:
            page_num = max(1, int(request.query_params.get("page", "1")))
        except (TypeError, ValueError):
            page_num = 1

        if template is None:
            return Response({
                "count": 0, "next": None, "previous": None,
                "page": page_num, "page_size": page_size,
                "results": [],
            })

        current_start, _current_end = current_week_period(
            ctx.program, org, today=today,
        )

        # Window the history at the program start when present so returning
        # Madrichim can scroll their whole program (Story 65 c5); fall back
        # to ``max_page_size`` weeks for previewers / programs without a
        # start date. Cap at ``current_start`` so a pre-start submission
        # (e.g. dev fixture) still renders the current-week row.
        program_start = ctx.program.start_date
        max_weeks = paginator.max_page_size
        fallback_start = current_start - timedelta(days=7 * (max_weeks - 1))
        bounded_start = min(
            program_start if program_start else fallback_start,
            current_start,
        )

        total_weeks = max(
            1,
            ((current_start - bounded_start).days // 7) + 1,
        )
        start_offset = (page_num - 1) * page_size
        end_offset = min(start_offset + page_size, total_weeks)

        page_periods: list[tuple[date_type, date_type]] = []
        for idx in range(start_offset, end_offset):
            period_start = current_start - timedelta(days=7 * idx)
            if period_start < bounded_start:
                break
            page_periods.append((period_start, period_start + timedelta(days=6)))

        if not page_periods:
            return Response({
                "count": total_weeks,
                "next": None,
                "previous": page_num - 1 if page_num > 1 else None,
                "page": page_num,
                "page_size": page_size,
                "results": [],
            })

        window_start = page_periods[-1][0]
        window_end = page_periods[0][1]
        reflections_qs = Reflection.all_objects.filter(
            author=viewer,
            subject=viewer,
            template=template,
            period_start__gte=window_start,
            period_end__lte=window_end,
        ).order_by("-period_start", "-submitted_at")

        by_period_start: dict[date_type, Reflection] = {}
        for r in reflections_qs:
            if r.period_start not in by_period_start:
                by_period_start[r.period_start] = r

        results: list[dict] = []
        for period_start, period_end in page_periods:
            reflection = by_period_start.get(period_start)
            results.append({
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "submitted": reflection is not None and reflection.is_complete,
                "reflection_id": reflection.id if reflection else None,
                "language": reflection.language if reflection else None,
                "submitted_at": (
                    reflection.submitted_at.isoformat()
                    if reflection and reflection.submitted_at else None
                ),
                "preview": (
                    _preview_from_answers(reflection.answers)
                    if reflection else ""
                ),
                "editable": (
                    reflection is not None and period_start == current_start
                ),
            })

        has_next = end_offset < total_weeks
        has_previous = page_num > 1
        return Response({
            "count": total_weeks,
            "next": page_num + 1 if has_next else None,
            "previous": page_num - 1 if has_previous else None,
            "page": page_num,
            "page_size": page_size,
            "results": results,
        })


class MadrichReflectionCreateView(APIView):
    """POST a Madrich weekly self-reflection (Story 62)."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["post", "head", "options"]

    def post(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        viewer, org, today = ctx.person, ctx.organization, ctx.today

        ser = MadrichReflectionCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        payload = ser.validated_data

        template = madrich_template(org, ctx.program)
        if template is None:
            msg = "No Madrich reflection template configured."
            raise PermissionDenied(msg)

        answers = dict(payload["answers"] or {})
        ok, err = _validate_answers(template, answers)
        if not ok:
            return err

        period_start, period_end = current_week_period(
            ctx.program, org, today=today,
        )

        def _create_reflection():
            reflection = Reflection(
                organization=org,
                program=ctx.program,
                subject=viewer,
                author=viewer,
                assignment_group=None,
                template=template,
                submitted_by=request.user,
                period_start=period_start,
                period_end=period_end,
                answers=answers,
                language=payload["language"],
                team_visibility=Reflection.TeamVisibility.TEAM,
                is_complete=True,
                client_submission_id=payload["client_submission_id"],
            )
            reflection.full_clean()
            reflection.save()
            return reflection

        try:
            reflection, created = idempotent_create(
                Reflection,
                program=ctx.program,
                client_submission_id=payload["client_submission_id"],
                create_fn=_create_reflection,
            )
        except DjangoValidationError as exc:
            body = exc.message_dict if hasattr(exc, "message_dict") else str(exc)
            return Response(body, status=status.HTTP_400_BAD_REQUEST)

        if not created:
            return Response(reflection_response(reflection), status=status.HTTP_200_OK)

        audit_module.created(
            ctx.membership, reflection,
            after_state=reflection_snapshot(reflection),
            content_type="reflection",
        )
        invalidate_dashboard_for_viewers(org, {viewer.id}, today)
        return Response(reflection_response(reflection), status=status.HTTP_201_CREATED)


class MadrichReflectionDetailView(APIView):
    """PATCH a Madrich self-reflection while its week is open (Story 62 c5-6)."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["patch", "head", "options"]

    def patch(self, request, reflection_id: int, *args, **kwargs):
        ctx = viewer_or_403(request)
        viewer, org, today = ctx.person, ctx.organization, ctx.today

        reflection = (
            Reflection.all_objects.filter(id=reflection_id, organization=org)
            .select_related("template", "program")
            .first()
        )
        if reflection is None:
            return Response(
                {"detail": "Reflection not found."}, status=status.HTTP_404_NOT_FOUND,
            )
        if reflection.author_id != viewer.id or reflection.subject_id != viewer.id:
            msg = "You can only edit your own reflection."
            raise PermissionDenied(msg)
        enforce_period_edit_window(reflection, today)

        ser = MadrichReflectionUpdateSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        payload = ser.validated_data

        before = reflection_snapshot(reflection)

        if "answers" in payload:
            answers = dict(payload["answers"])
            ok, err = _validate_answers(reflection.template, answers)
            if not ok:
                return err
        else:
            answers = reflection.answers

        language = payload.get("language", reflection.language)
        reflection.answers = answers
        reflection.language = language
        try:
            reflection.full_clean()
        except DjangoValidationError as exc:
            body = exc.message_dict if hasattr(exc, "message_dict") else str(exc)
            return Response(body, status=status.HTTP_400_BAD_REQUEST)
        reflection.save()
        after = reflection_snapshot(reflection)

        if before != after:
            actor_membership = (
                Membership.objects.filter(
                    person=viewer, program=reflection.program, is_active=True,
                )
                .order_by("-created_at")
                .first()
            )
            audit_module.edited(
                actor_membership or request.user,
                reflection, before, after,
                content_type="reflection",
            )

        invalidate_dashboard_for_viewers(org, {viewer.id}, today)
        return Response(reflection_response(reflection), status=status.HTTP_200_OK)
