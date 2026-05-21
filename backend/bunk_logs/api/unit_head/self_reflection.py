"""UH self-reflection write + history endpoints (Stories 16, 17).

POST / PATCH semantics mirror the counselor self-reflection module:
the ``day_off`` shortcut, today-only edit window (``enforce_edit_window``),
idempotency via ``client_submission_id``, audit events, and dashboard
cache invalidation all behave identically. Differences:

* Authentication requires an active ``unit_head`` Membership (the
  shared ``viewer_or_403`` raises 403 otherwise).
* ``answers.bunk_concerns_bunks`` is validated against the viewer's
  supervised bunk IDs — UH can flag only bunks they supervise (Story
  16 criterion 7, UH2). Invalid IDs raise 403 rather than 400
  because the request is making a permission-relevant claim.
* History rows (Story 17) emit ``editable`` only when the cursor is
  today AND the row exists. UH reflections from OTHER UHs are not
  visible (UH6) — the queryset is already scoped to author=viewer.
"""

from __future__ import annotations

from datetime import date as date_type
from datetime import timedelta

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
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
from bunk_logs.core.models import reflection_snapshot
from bunk_logs.core.models import validate_reflection_answers
from bunk_logs.core.translation import enqueue_translation_for_reflection

from .common import enforce_edit_window
from .common import is_day_off_answer
from .common import supervised_bunk_ids
from .common import unit_head_self_template
from .common import validate_bunk_concerns_ids
from .common import viewer_or_403
from .serializers import UnitHeadSelfReflectionCreateSerializer
from .serializers import UnitHeadSelfReflectionUpdateSerializer


class UnitHeadSelfReflectionHistoryPagination(PageNumberPagination):
    """Same shape as the counselor history pagination."""

    page_size = 14
    page_size_query_param = "page_size"
    max_page_size = 60


def _preview_from_answers(answers: dict | None, max_len: int = 120) -> str:
    if not answers:
        return ""
    for value in answers.values():
        if isinstance(value, str) and value.strip():
            text = value.strip()
            return text if len(text) <= max_len else text[: max_len - 1] + "\u2026"
    return ""


def _day_off_answers() -> dict:
    return {"day_off": True}


class UnitHeadSelfReflectionHistoryView(APIView):
    """Story 17: prior UH self-reflections + gaps + day-off indicators."""

    permission_classes = [IsAuthenticated]
    pagination_class = UnitHeadSelfReflectionHistoryPagination

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        viewer = ctx.person
        today = ctx.today

        template = unit_head_self_template(ctx.organization, ctx.program)
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
                "submitted_at": (
                    reflection.submitted_at.isoformat()
                    if reflection and reflection.submitted_at else None
                ),
                "preview": (
                    _preview_from_answers(reflection.answers)
                    if reflection and not is_day_off_answer(reflection) else ""
                ),
                "editable": reflection is not None and cursor == today,
                "referenced_bunk_ids": (
                    list(reflection.answers.get("bunk_concerns_bunks") or [])
                    if reflection and isinstance(reflection.answers, dict) else []
                ),
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


def _validate_answers_for_template(template, answers: dict) -> tuple[bool, Response | None]:
    """Run the JSON-schema validator; coerce ValidationError to a DRF 400 response."""
    try:
        validate_reflection_answers(template.schema, answers)
    except DjangoValidationError as e:
        body = e.message_dict if hasattr(e, "message_dict") else {"answers": str(e)}
        return False, Response(body, status=status.HTTP_400_BAD_REQUEST)
    return True, None


class UnitHeadSelfReflectionCreateView(APIView):
    """POST a UH self-reflection for today (Story 16)."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["post", "head", "options"]

    def post(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        viewer, org, today = ctx.person, ctx.organization, ctx.today

        serializer = UnitHeadSelfReflectionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        template = unit_head_self_template(org, ctx.program)
        if template is None:
            msg = "No Unit Head self-reflection template configured."
            raise PermissionDenied(msg)

        existing = find_existing_by_client_submission_id(
            Reflection, program=ctx.program,
            client_submission_id=payload["client_submission_id"],
        )
        if existing is not None:
            return Response(reflection_response(existing), status=status.HTTP_200_OK)

        if payload["day_off"]:
            answers = _day_off_answers()
        else:
            answers = dict(payload.get("answers") or {})
            # Coerce + permission-check bunk_concerns_bunks before schema
            # validation so we surface 403s before structural complaints.
            supervised = supervised_bunk_ids(ctx.membership, today=today)
            answers["bunk_concerns_bunks"] = validate_bunk_concerns_ids(
                answers.get("bunk_concerns_bunks"), supervised,
            )
            ok, err = _validate_answers_for_template(template, answers)
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
            except DjangoValidationError as e:
                body = e.message_dict if hasattr(e, "message_dict") else str(e)
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
        # Also bump the UH dashboard cache since the self-reflection
        # section reads from it.
        from django.core.cache import cache
        cache.delete(f"unit_head_dashboard:{org.id}:{viewer.id}:{today.isoformat()}")

        return Response(reflection_response(reflection), status=status.HTTP_201_CREATED)


class UnitHeadSelfReflectionDetailView(APIView):
    """PATCH a UH self-reflection within today's edit window (Story 17)."""

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
            msg = "You can only edit your own self-reflection."
            raise PermissionDenied(msg)
        enforce_edit_window(reflection, org)

        serializer = UnitHeadSelfReflectionUpdateSerializer(
            data=request.data, partial=True,
        )
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        before = reflection_snapshot(reflection)
        supervised = supervised_bunk_ids(ctx.membership, today=today)

        if "day_off" in payload:
            if payload["day_off"]:
                answers = _day_off_answers()
            else:
                answers = dict(payload.get("answers") or reflection.answers or {})
                answers["bunk_concerns_bunks"] = validate_bunk_concerns_ids(
                    answers.get("bunk_concerns_bunks"), supervised,
                )
                ok, err = _validate_answers_for_template(
                    reflection.template, answers,
                )
                if not ok:
                    return err
        elif "answers" in payload:
            answers = dict(payload["answers"])
            answers["bunk_concerns_bunks"] = validate_bunk_concerns_ids(
                answers.get("bunk_concerns_bunks"), supervised,
            )
            ok, err = _validate_answers_for_template(reflection.template, answers)
            if not ok:
                return err
        else:
            answers = reflection.answers

        language = payload.get("language", reflection.language)
        reflection.answers = answers
        reflection.language = language
        try:
            reflection.full_clean()
        except DjangoValidationError as e:
            body = e.message_dict if hasattr(e, "message_dict") else str(e)
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
        from django.core.cache import cache
        cache.delete(f"unit_head_dashboard:{org.id}:{viewer.id}:{today.isoformat()}")

        return Response(reflection_response(reflection), status=status.HTTP_200_OK)
