"""Kitchen Staff self-reflection endpoints — Stories 40-44.

Endpoints
---------
POST  /api/v1/kitchen-staff/reflection/           — submit (Story 40)
PATCH /api/v1/kitchen-staff/reflection/<id>/      — edit within rollover window (Story 41)
GET   /api/v1/kitchen-staff/reflection/history/   — paginated history (Story 41 criterion 7)

Key invariants
--------------
* Reflection language defaults to ``Person.preferred_language``.
* Non-English submissions enqueue ``translate_reflection_to_english`` via
  ``enqueue_translation_for_reflection``.
* On edit: ``language`` field unchanged unless user explicitly sends it (Story 41 criterion 6).
* Response always embeds translation state so leadership readers see
  translated/pending/failed status (Story 44).
* Author's own history always in original language (Story 41 criterion 9).
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

from bunk_logs.api.counselor.common import find_existing_by_client_submission_id
from bunk_logs.api.counselor.common import invalidate_dashboard_for_viewers
from bunk_logs.api.counselor.responses import reflection_response
from bunk_logs.core import audit as audit_module
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import TranslationRecord
from bunk_logs.core.models import reflection_snapshot
from bunk_logs.core.models import validate_reflection_answers
from bunk_logs.core.translation import enqueue_translation_for_reflection

from .common import enforce_edit_window
from .common import is_day_off_answer
from .common import kitchen_staff_template
from .common import viewer_or_403


class KitchenStaffReflectionCreateSerializer(serializers.Serializer):
    answers = serializers.JSONField(required=False)
    day_off = serializers.BooleanField(default=False)
    language = serializers.CharField(max_length=10, default="en")
    client_submission_id = serializers.UUIDField()

    def validate(self, attrs):
        if not attrs.get("day_off") and not attrs.get("answers"):
            raise serializers.ValidationError(
                {"answers": "answers is required unless day_off is true."},
            )
        return attrs


class KitchenStaffReflectionUpdateSerializer(serializers.Serializer):
    answers = serializers.JSONField(required=False)
    day_off = serializers.BooleanField(required=False)
    language = serializers.CharField(max_length=10, required=False)

    def validate(self, attrs):
        if not attrs:
            msg = "At least one field must be provided."
            raise serializers.ValidationError(msg)
        return attrs


class KitchenStaffReflectionHistoryPagination(PageNumberPagination):
    page_size = 14
    page_size_query_param = "page_size"
    max_page_size = 60


def _day_off_answers() -> dict:
    return {"day_off": True}


def _preview_from_answers(answers: dict | None, max_len: int = 120) -> str:
    if not answers:
        return ""
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


def _translation_state(reflection: Reflection) -> dict | None:
    """Return embedded translation state for leadership readers (Story 44)."""
    lang = reflection.language or "en"
    if lang == "en":
        return None
    record = TranslationRecord.latest_for("reflection", reflection.pk)
    if record is None:
        return {
            "status": "pending",
            "source_language": lang,
            "target_language": "en",
            "translated_text": "",
            "model_id": "",
        }
    return {
        "id": str(record.id),
        "status": record.status,
        "source_language": record.source_language,
        "target_language": record.target_language,
        "translated_text": record.translated_text,
        "model_id": record.model_id,
    }


def _reflection_payload(reflection: Reflection) -> dict:
    """Full reflection payload including translation embed."""
    base = reflection_response(reflection)
    base["translation"] = _translation_state(reflection)
    return base


class KitchenStaffReflectionHistoryView(APIView):
    """Paginated reflection history for the authenticated Kitchen Staff member."""

    permission_classes = [IsAuthenticated]
    pagination_class = KitchenStaffReflectionHistoryPagination

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        viewer = ctx.person
        today = ctx.today

        template = kitchen_staff_template(ctx.organization, ctx.program)
        if template is None:
            return Response({
                "count": 0, "next": None, "previous": None,
                "page": 1, "page_size": self.pagination_class.page_size,
                "results": [],
            })

        paginator = self.pagination_class()
        page_size = paginator.get_page_size(request) or paginator.page_size
        try:
            page_num = max(1, int(request.query_params.get("page", "1")))
        except (TypeError, ValueError):
            page_num = 1

        max_days = paginator.max_page_size * 5
        oldest = today - timedelta(days=max_days - 1)
        start_offset = (page_num - 1) * page_size
        end_offset = start_offset + page_size - 1
        period_end_window = today - timedelta(days=start_offset)
        period_start_window = max(today - timedelta(days=end_offset), oldest)

        reflections_qs = (
            Reflection.all_objects.filter(
                author=viewer,
                subject=viewer,
                template=template,
                period_start__gte=period_start_window,
                period_end__lte=period_end_window,
            )
            .order_by("-period_start", "-submitted_at")
        )

        by_date: dict[date_type, Reflection] = {}
        for r in reflections_qs:
            if r.period_start not in by_date:
                by_date[r.period_start] = r

        results: list[dict] = []
        cursor = period_end_window
        while cursor >= period_start_window and len(results) < page_size:
            reflection = by_date.get(cursor)
            results.append({
                "date": cursor.isoformat(),
                "submitted": reflection is not None and reflection.is_complete,
                "is_day_off": is_day_off_answer(reflection) if reflection else False,
                "reflection_id": reflection.id if reflection else None,
                "language": reflection.language if reflection else None,
                "submitted_at": (
                    reflection.submitted_at.isoformat()
                    if reflection and reflection.submitted_at else None
                ),
                "preview": (
                    _preview_from_answers(reflection.answers)
                    if reflection and not is_day_off_answer(reflection) else ""
                ),
                "editable": reflection is not None and cursor == today,
            })
            cursor -= timedelta(days=1)

        total_count = max_days
        has_next = page_num * page_size < total_count
        has_previous = page_num > 1
        return Response({
            "count": total_count,
            "next": page_num + 1 if has_next else None,
            "previous": page_num - 1 if has_previous else None,
            "page": page_num,
            "page_size": page_size,
            "results": results,
        })


class KitchenStaffReflectionCreateView(APIView):
    """POST a Kitchen Staff self-reflection for today (Story 40)."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["post", "head", "options"]

    def post(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        viewer, org, today = ctx.person, ctx.organization, ctx.today

        ser = KitchenStaffReflectionCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        payload = ser.validated_data

        template = kitchen_staff_template(org, ctx.program)
        if template is None:
            msg = "No Kitchen Staff reflection template configured."
            raise PermissionDenied(msg)

        existing = find_existing_by_client_submission_id(
            Reflection, program=ctx.program,
            client_submission_id=payload["client_submission_id"],
        )
        if existing is not None:
            return Response(_reflection_payload(existing), status=status.HTTP_200_OK)

        if payload["day_off"]:
            answers = _day_off_answers()
        else:
            answers = dict(payload.get("answers") or {})
            ok, err = _validate_answers(template, answers)
            if not ok:
                return err

        with transaction.atomic():
            reflection = Reflection(
                organization=org,
                program=ctx.program,
                subject=viewer,
                author=viewer,
                assignment_group=None,
                template=template,
                submitted_by=request.user,
                period_start=today,
                period_end=today,
                answers=answers,
                language=payload["language"],
                team_visibility=Reflection.TeamVisibility.SUPERVISORS_ONLY,
                is_complete=True,
                client_submission_id=payload["client_submission_id"],
            )
            try:
                reflection.full_clean()
            except DjangoValidationError as exc:
                body = exc.message_dict if hasattr(exc, "message_dict") else str(exc)
                return Response(body, status=status.HTTP_400_BAD_REQUEST)
            reflection.save()

        audit_module.created(
            ctx.membership,
            reflection,
            after_state=reflection_snapshot(reflection),
            content_type="reflection",
        )
        if not payload["day_off"]:
            enqueue_translation_for_reflection(reflection)
        invalidate_dashboard_for_viewers(org, {viewer.id}, today)

        return Response(_reflection_payload(reflection), status=status.HTTP_201_CREATED)


class KitchenStaffReflectionDetailView(APIView):
    """PATCH a Kitchen Staff self-reflection within today's edit window (Story 41)."""

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
            return Response({"detail": "Reflection not found."}, status=status.HTTP_404_NOT_FOUND)
        if reflection.author_id != viewer.id or reflection.subject_id != viewer.id:
            msg = "You can only edit your own reflection."
            raise PermissionDenied(msg)
        enforce_edit_window(reflection, org)

        ser = KitchenStaffReflectionUpdateSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        payload = ser.validated_data

        before = reflection_snapshot(reflection)

        if "day_off" in payload:
            if payload["day_off"]:
                answers = _day_off_answers()
            else:
                answers = dict(payload.get("answers") or reflection.answers or {})
                ok, err = _validate_answers(reflection.template, answers)
                if not ok:
                    return err
        elif "answers" in payload:
            answers = dict(payload["answers"])
            ok, err = _validate_answers(reflection.template, answers)
            if not ok:
                return err
        else:
            answers = reflection.answers

        # Story 41 criterion 6: language only changes when user explicitly sends it
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
                reflection,
                before, after,
                content_type="reflection",
            )
        if (
            before.get("answers") != after.get("answers")
            or before.get("language") != after.get("language")
        ) and not is_day_off_answer(reflection):
            enqueue_translation_for_reflection(reflection)

        invalidate_dashboard_for_viewers(org, {viewer.id}, today)
        return Response(_reflection_payload(reflection), status=status.HTTP_200_OK)
