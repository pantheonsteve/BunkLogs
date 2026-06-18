"""LT self-reflection write + edit endpoints — Story 50.

POST  /api/v1/leadership-team/self-reflection/                — submit
PATCH /api/v1/leadership-team/self-reflection/<id>/           — edit within period

Differences from the kitchen / counselor / UH self-reflection modules:

* Template is ``leadership-team-self-reflection`` (biweekly by default).
* Edit window is the current period, not a single rollover day — we
  enforce ``period_start <= today <= period_end`` instead of
  ``is_editable_today``.
* The ``is_private`` payload toggle restricts visibility to the
  author + Admin only by mapping to
  ``Reflection.TeamVisibility.SUPERVISORS_ONLY`` AND marking the row
  ``is_sensitive=True``. That combination flips the visibility model
  to the sensitive-variant audience for ``LEADERSHIP_TEAM_SELF_REFLECTION``
  ({admin} only) per ``content_visibility._SENSITIVE_AUDIENCES``.

Notes on history:
* The dashboard reads "current period" state; a paginated history list
  endpoint lands in PR B with the broader templates + responses surface.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.api.counselor.responses import reflection_response
from bunk_logs.core import audit as audit_module
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import reflection_snapshot
from bunk_logs.core.models import validate_reflection_answers
from bunk_logs.core.submission import idempotent_create
from bunk_logs.core.translation import enqueue_translation_for_reflection

from .common import leadership_team_self_template
from .common import resolve_period
from .common import viewer_or_403
from .serializers import LTSelfReflectionCreateSerializer
from .serializers import LTSelfReflectionUpdateSerializer


def _validate_answers_for_template(template, answers: dict) -> tuple[bool, Response | None]:
    try:
        validate_reflection_answers(template.schema, answers)
    except DjangoValidationError as exc:
        body = exc.message_dict if hasattr(exc, "message_dict") else {"answers": str(exc)}
        return False, Response(body, status=status.HTTP_400_BAD_REQUEST)
    return True, None


def _enforce_period(reflection: Reflection, today) -> None:
    if reflection.period_start <= today <= reflection.period_end:
        return
    msg = "This reflection can no longer be edited (the period has closed)."
    raise PermissionDenied(msg)


def _bust_dashboard_cache(org_id: int, viewer_id: int, today) -> None:
    from django.core.cache import cache
    cache.delete(f"leadership_team_dashboard:{org_id}:{viewer_id}:{today.isoformat()}")


class LeadershipTeamSelfReflectionCreateView(APIView):
    """POST an LT self-reflection for the current period (Story 50)."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["post", "head", "options"]

    def post(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        viewer, org, today = ctx.person, ctx.organization, ctx.today

        ser = LTSelfReflectionCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        payload = ser.validated_data

        template = leadership_team_self_template(org, ctx.program)
        if template is None:
            msg = "No Leadership Team self-reflection template configured."
            raise PermissionDenied(msg)

        period_start, period_end = resolve_period(
            template, anchor=today, program=ctx.program,
        )

        answers = dict(payload.get("answers") or {})
        ok, err = _validate_answers_for_template(template, answers)
        if not ok:
            return err

        is_private = bool(payload.get("is_private"))
        team_visibility = (
            Reflection.TeamVisibility.SUPERVISORS_ONLY
            if is_private
            else Reflection.TeamVisibility.TEAM
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
                team_visibility=team_visibility,
                is_sensitive=is_private,
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
        enqueue_translation_for_reflection(reflection)
        _bust_dashboard_cache(org.id, viewer.id, today)
        return Response(reflection_response(reflection), status=status.HTTP_201_CREATED)


class LeadershipTeamSelfReflectionDetailView(APIView):
    """PATCH an LT self-reflection within its period (Story 50 c7)."""

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
        _enforce_period(reflection, today)

        ser = LTSelfReflectionUpdateSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        payload = ser.validated_data

        before = reflection_snapshot(reflection)

        if "answers" in payload:
            answers = dict(payload["answers"])
            ok, err = _validate_answers_for_template(reflection.template, answers)
            if not ok:
                return err
        else:
            answers = reflection.answers

        language = payload.get("language", reflection.language)
        reflection.answers = answers
        reflection.language = language

        if "is_private" in payload:
            is_private = bool(payload["is_private"])
            reflection.team_visibility = (
                Reflection.TeamVisibility.SUPERVISORS_ONLY
                if is_private
                else Reflection.TeamVisibility.TEAM
            )
            reflection.is_sensitive = is_private

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
        if before.get("answers") != after.get("answers") or before.get("language") != after.get("language"):
            enqueue_translation_for_reflection(reflection)

        _bust_dashboard_cache(org.id, viewer.id, today)
        return Response(reflection_response(reflection), status=status.HTTP_200_OK)
