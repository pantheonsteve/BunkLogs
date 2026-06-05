"""``GET /api/v1/counselor/camper-reflections/?date=YYYY-MM-DD`` — Story 3.

Returns the bunk roster(s) for the viewer with each camper's submitted /
not-submitted status for the requested date. Off-camp campers (per
``CamperDayState``) appear in a dedicated sub-section and don't count
toward "expected".

The view of past dates is read-only (Story 6 criterion 4 — extended to
camper reflections per Story 4): the ``editable`` flag on the response
and on each row tells the client whether to render the Edit affordance.
"""

from __future__ import annotations

from datetime import date as date_type

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core import audit as audit_module
from bunk_logs.core.flags import raise_flag_from_camper_reflection
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import reflection_snapshot
from bunk_logs.core.models import validate_reflection_answers
from bunk_logs.core.translation import enqueue_translation_for_reflection

from .common import bunk_camper_persons
from .common import camper_reflection_template
from .common import co_counselor_person_ids
from .common import enforce_edit_window
from .common import find_existing_by_client_submission_id
from .common import invalidate_dashboard_for_viewers
from .common import latest_camper_reflection_per_subject
from .common import off_camp_camper_ids
from .common import person_display_name
from .common import viewer_bunk_groups
from .common import viewer_can_edit_camper_reflection
from .common import viewer_or_403
from .responses import reflection_response
from .serializers import CamperReflectionCreateSerializer
from .serializers import CamperReflectionUpdateSerializer


def _parse_iso_date(value: str | None, default: date_type) -> date_type | None:
    if not value:
        return default
    try:
        return date_type.fromisoformat(value)
    except (TypeError, ValueError):
        return None


class CamperReflectionListView(APIView):
    """Bunk roster with per-camper submission state for a date."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        viewer = ctx.person
        org = ctx.organization
        today = ctx.today

        target = _parse_iso_date(request.query_params.get("date"), today)
        if target is None:
            return Response(
                {"detail": "Invalid 'date' query parameter; expected YYYY-MM-DD."},
                status=400,
            )

        primary_membership = (
            Membership.objects.filter(person=viewer, is_active=True)
            .select_related("program")
            .order_by("-created_at")
            .first()
        )
        if primary_membership is None or primary_membership.program is None:
            return Response({
                "date": target.isoformat(),
                "editable": target == today,
                "bunks": [],
            })
        program = primary_membership.program

        bunks = viewer_bunk_groups(viewer)
        if not bunks:
            return Response({
                "date": target.isoformat(),
                "editable": target == today,
                "bunks": [],
            })

        template = camper_reflection_template(org, program)
        roster_by_bunk = bunk_camper_persons(bunks)
        all_camper_ids: set[int] = set()
        for campers in roster_by_bunk.values():
            all_camper_ids.update(p.id for p in campers)

        off_camp_ids = off_camp_camper_ids(org, target, camper_ids=all_camper_ids)
        reflections_by_subject = (
            latest_camper_reflection_per_subject(template, bunks, target, target)
            if template is not None
            else {}
        )

        date_is_today = target == today
        bunks_payload = []
        for bunk in bunks:
            campers = roster_by_bunk.get(bunk.id, [])
            row_campers = []
            off_camp_rows = []
            covered = 0
            for camper in campers:
                base = {
                    "id": camper.id,
                    "name": person_display_name(camper),
                    "preferred_name": camper.preferred_name or camper.first_name,
                    "first_name": camper.first_name,
                    "last_initial": (camper.last_name or "")[:1],
                }
                if camper.id in off_camp_ids:
                    # Off-camp rows are surfaced separately and don't get
                    # status / submitter / editable fields — they aren't
                    # actionable in this UI.
                    off_camp_rows.append(base)
                    continue

                reflection = reflections_by_subject.get(camper.id)
                submitted = reflection is not None
                if submitted:
                    covered += 1
                    author_person = reflection.author
                    is_self = author_person == viewer if author_person else False
                    submitter = {
                        "is_self": is_self,
                        # Per Story 3 criterion 3 — show submitter name only when
                        # it isn't the viewer themself.
                        "name": person_display_name(author_person) if not is_self else None,
                    }
                else:
                    submitter = None

                row = {
                    **base,
                    "submitted": submitted,
                    "reflection_id": reflection.id if reflection else None,
                    "submitted_at": (
                        reflection.submitted_at.isoformat()
                        if reflection and reflection.submitted_at
                        else None
                    ),
                    "submitter": submitter,
                    "editable": submitted and date_is_today,
                }
                row_campers.append(row)

            bunks_payload.append({
                "id": bunk.id,
                "slug": bunk.slug,
                "name": bunk.name,
                "covered": covered,
                "total": len(row_campers),
                "campers": row_campers,
                "off_camp": off_camp_rows,
            })

        return Response({
            "date": target.isoformat(),
            "editable": date_is_today,
            "template": (
                {
                    "id": template.id,
                    "slug": template.slug,
                    "name": template.name,
                    "version": template.version,
                }
                if template is not None
                else None
            ),
            "bunks": bunks_payload,
        })

    def post(self, request, *args, **kwargs):
        """Submit a camper reflection (Story 3).

        Idempotent on ``(program, client_submission_id)`` — duplicate POSTs
        get the existing row back with HTTP 200 so the offline queue can
        replay safely. New submissions return HTTP 201 with the full
        reflection payload.
        """
        ctx = viewer_or_403(request)
        viewer, org, today = ctx.person, ctx.organization, ctx.today

        serializer = CamperReflectionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        primary_membership = (
            Membership.objects.filter(person=viewer, is_active=True)
            .select_related("program")
            .order_by("-created_at")
            .first()
        )
        if primary_membership is None or primary_membership.program is None:
            msg = "No active program membership."
            raise PermissionDenied(msg)
        program = primary_membership.program

        existing = find_existing_by_client_submission_id(
            Reflection, program=program,
            client_submission_id=payload["client_submission_id"],
        )
        if existing is not None:
            raise_flag_from_camper_reflection(
                existing, raised_by_membership=primary_membership,
            )
            return Response(reflection_response(existing), status=status.HTTP_200_OK)

        bunk = AssignmentGroup.all_objects.filter(
            id=payload["assignment_group_id"],
            organization=org,
            group_type="bunk",
            is_active=True,
        ).first()
        if bunk is None:
            raise PermissionDenied({"assignment_group_id": "Bunk not found."})

        # Story 3 criterion 1: viewer must be an active author on the bunk.
        is_author = AssignmentGroupMembership.all_objects.filter(
            group=bunk, person=viewer, role_in_group="author", is_active=True,
        ).exists()
        if not is_author:
            msg = "You are not an author on this bunk."
            raise PermissionDenied(msg)

        # Story 3 criterion 2: subject must be an active camper in the bunk roster.
        roster_camper_ids = set(
            AssignmentGroupMembership.all_objects.filter(
                group=bunk, role_in_group="subject", is_active=True,
            ).values_list("person_id", flat=True),
        )
        if payload["subject_id"] not in roster_camper_ids:
            raise PermissionDenied(
                {"subject_id": "Camper is not on this bunk."},
            )

        # Story 3 criterion 8: off-camp campers can't have reflections submitted.
        off_camp = off_camp_camper_ids(org, today, camper_ids=[payload["subject_id"]])
        if payload["subject_id"] in off_camp:
            raise PermissionDenied(
                {"subject_id": "Camper is marked off-camp today."},
            )

        template = camper_reflection_template(org, program)
        if template is None:
            msg = "No camper-reflection template configured for this program."
            raise PermissionDenied(msg)

        try:
            validate_reflection_answers(template.schema, payload["answers"])
        except DjangoValidationError as e:
            return Response(
                e.message_dict if hasattr(e, "message_dict") else {"answers": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            reflection = Reflection(
                organization=org,
                program=program,
                subject_id=payload["subject_id"],
                author=viewer,
                assignment_group=bunk,
                template=template,
                submitted_by=request.user,
                period_start=today,
                period_end=today,
                answers=payload["answers"],
                language=payload["language"],
                team_visibility=payload["team_visibility"],
                is_complete=True,
                client_submission_id=payload["client_submission_id"],
            )
            try:
                reflection.full_clean()
            except DjangoValidationError as e:
                return Response(
                    e.message_dict if hasattr(e, "message_dict") else str(e),
                    status=status.HTTP_400_BAD_REQUEST,
                )
            reflection.save()
            raise_flag_from_camper_reflection(
                reflection, raised_by_membership=primary_membership,
            )

        audit_module.created(
            primary_membership,
            reflection,
            after_state=reflection_snapshot(reflection),
            content_type="reflection",
        )
        enqueue_translation_for_reflection(reflection)
        _invalidate_dashboards_for_bunk(org, viewer, bunk, today)

        return Response(reflection_response(reflection), status=status.HTTP_201_CREATED)


class CamperReflectionDetailView(APIView):
    """PATCH for a single camper reflection (Story 4)."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["patch", "head", "options"]

    def patch(self, request, reflection_id: int, *args, **kwargs):
        ctx = viewer_or_403(request)
        viewer, org, today = ctx.person, ctx.organization, ctx.today

        reflection = Reflection.all_objects.filter(
            id=reflection_id, organization=org,
        ).select_related("template", "assignment_group", "program").first()
        if reflection is None:
            return Response(
                {"detail": "Reflection not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Story 4 criterion 2: any current bunk author may edit (not just
        # the original author). The audit row records who actually edited.
        if not viewer_can_edit_camper_reflection(viewer, reflection):
            msg = "You are not an author on this reflection's bunk."
            raise PermissionDenied(msg)
        enforce_edit_window(reflection, org)

        serializer = CamperReflectionUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        before = reflection_snapshot(reflection)

        answers = payload.get("answers", reflection.answers)
        language = payload.get("language", reflection.language)
        team_visibility = payload.get("team_visibility", reflection.team_visibility)

        if "answers" in payload:
            try:
                validate_reflection_answers(reflection.template.schema, answers)
            except DjangoValidationError as e:
                return Response(
                    e.message_dict if hasattr(e, "message_dict") else {"answers": str(e)},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        reflection.answers = answers
        reflection.language = language
        reflection.team_visibility = team_visibility

        try:
            reflection.full_clean()
        except DjangoValidationError as e:
            return Response(
                e.message_dict if hasattr(e, "message_dict") else str(e),
                status=status.HTTP_400_BAD_REQUEST,
            )
        reflection.save()
        after = reflection_snapshot(reflection)

        actor_membership = (
            Membership.objects.filter(
                person=viewer, program=reflection.program, is_active=True,
            )
            .order_by("-created_at")
            .first()
        )
        raise_flag_from_camper_reflection(
            reflection, raised_by_membership=actor_membership,
        )

        if before != after:
            audit_module.edited(
                actor_membership or request.user,
                reflection,
                before,
                after,
                content_type="reflection",
            )
        if (
            before.get("answers") != after.get("answers")
            or before.get("language") != after.get("language")
        ):
            enqueue_translation_for_reflection(reflection)
        if reflection.assignment_group_id:
            _invalidate_dashboards_for_bunk(
                org, viewer, reflection.assignment_group, today,
            )

        return Response(reflection_response(reflection), status=status.HTTP_200_OK)


def _invalidate_dashboards_for_bunk(org, viewer, bunk, today):
    """Bust the dashboard cache for viewer + all co-counselors on this bunk.

    Used by camper-reflection writes so a counselor's submission shows up on
    their bunkmate's dashboard within seconds rather than after the 30s TTL
    expires (Story 2 criterion 5).
    """
    co_ids = co_counselor_person_ids(viewer, [bunk])
    invalidate_dashboard_for_viewers(org, co_ids | {viewer.id}, today)
