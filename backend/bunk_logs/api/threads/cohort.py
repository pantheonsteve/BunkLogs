"""Cohort feed endpoints — Step 4_9 §3, §4.5, §6.7.

GET  /api/v1/cohort/feed/              — posts visible to the caller
GET  /api/v1/cohort/members/           — who is in the caller's cohort(s)
POST /api/v1/cohort/shares/<id>/react/ — toggle a like
POST /api/v1/cohort/shares/<id>/hide/  — director moderation (soft, logged)

A cohort is a classroom ``AssignmentGroup``. A Madrich in several
classrooms gets the union, deduplicated by share id.
"""

from __future__ import annotations

from django.db.models import Count
from django.db.models import Q
from rest_framework import serializers
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import CohortShare
from bunk_logs.core.models import CohortShareModeration
from bunk_logs.core.models import EntryThread
from bunk_logs.core.models import Membership
from bunk_logs.core.models import ShareReaction
from bunk_logs.core.reflection_threads import unread_thread_ids

from .common import SUBJECT
from .common import ThreadViewer
from .common import display_name
from .common import share_payload
from .common import viewer_or_403


class CohortFeedPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class ShareHideSerializer(serializers.Serializer):
    is_hidden = serializers.BooleanField()


def _visible_group_ids(viewer: ThreadViewer) -> list[int]:
    """Classroom ids whose feed the caller may read.

    Madrichim see their own cohorts, faculty see the classrooms they
    author, and admins see every classroom in the program.
    """
    if viewer.is_admin and viewer.program:
        return list(
            AssignmentGroup.objects.filter(
                program=viewer.program, group_type="classroom", is_active=True,
            ).values_list("id", flat=True),
        )
    group_ids = set(viewer.cohort_ids)
    if viewer.is_faculty and viewer.program:
        from bunk_logs.api.classroom_challenges.common import classroom_group_ids_for_role

        group_ids.update(
            classroom_group_ids_for_role(
                viewer.person, viewer.program, role_in_group="author",
            ),
        )
    return sorted(group_ids)


class CohortFeedView(APIView):
    """Cohort posts newest first, with reaction and comment counts."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        viewer = viewer_or_403(request)
        group_ids = _visible_group_ids(viewer)
        if not group_ids:
            paginator = CohortFeedPagination()
            paginator.paginate_queryset(CohortShare.objects.none(), request, view=self)
            return paginator.get_paginated_response([])

        qs = CohortShare.objects.filter(assignment_group_id__in=group_ids)
        # Hidden posts stay visible to admins (so they can un-hide) and to
        # their own author, but disappear from everyone else's feed.
        if not viewer.is_admin:
            qs = qs.filter(Q(is_hidden=False) | Q(person=viewer.person))
        qs = (
            qs.select_related("person")
            .annotate(like_total=Count("reactions", distinct=True))
            .order_by("-created_at")
        )

        paginator = CohortFeedPagination()
        page = list(paginator.paginate_queryset(qs, request, view=self))
        share_ids = [s.id for s in page]

        liked = set(
            ShareReaction.all_objects.filter(
                cohort_share_id__in=share_ids,
                person=viewer.person,
                kind=ShareReaction.KIND_LIKE,
            ).values_list("cohort_share_id", flat=True),
        )
        threads = {
            row["cohort_share_id"]: (row["id"], row["comment_count"])
            for row in EntryThread.all_objects.filter(
                cohort_share_id__in=share_ids,
            )
            .annotate(comment_count=Count("messages", distinct=True))
            .values("id", "cohort_share_id", "comment_count")
        }
        unread = unread_thread_ids(
            viewer.person, [tid for tid, _ in threads.values()],
        )

        return paginator.get_paginated_response([
            share_payload(
                share,
                viewer=viewer,
                like_count=share.like_total,
                liked_by_me=share.id in liked,
                comment_count=threads.get(share.id, (None, 0))[1],
                thread_id=threads.get(share.id, (None, 0))[0],
                unread=threads.get(share.id, (None, 0))[0] in unread,
            )
            for share in page
        ])


class CohortMembersView(APIView):
    """People in the caller's cohort(s): name, grade level, initials."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        viewer = viewer_or_403(request)
        group_ids = _visible_group_ids(viewer)
        if not group_ids or viewer.program is None:
            return Response({"results": []})

        rows = (
            AssignmentGroupMembership.objects.filter(
                group_id__in=group_ids, role_in_group=SUBJECT, is_active=True,
            )
            .select_related("person", "group")
            .order_by("person__last_name", "person__first_name")
        )
        grades = dict(
            Membership.all_objects.filter(
                program=viewer.program,
                person_id__in=[r.person_id for r in rows],
                is_active=True,
            )
            .exclude(grade_level__isnull=True)
            .values_list("person_id", "grade_level"),
        )

        seen: set[int] = set()
        results = []
        for row in rows:
            if row.person_id in seen:
                continue
            seen.add(row.person_id)
            name = display_name(row.person)
            results.append({
                "id": row.person_id,
                "display_name": name,
                "initials": _initials(row.person),
                "grade_level": grades.get(row.person_id),
                "cohort": {"id": row.group_id, "name": row.group.name},
                "is_me": row.person_id == viewer.person.id,
            })
        return Response({"results": results})


def _initials(person) -> str:
    first = (person.preferred_name or person.first_name or "").strip()
    last = (person.last_name or "").strip()
    return f"{first[:1]}{last[:1]}".upper()


def _share_or_403(viewer: ThreadViewer, share_id: int) -> CohortShare:
    share = (
        CohortShare.objects.filter(id=share_id).select_related("person").first()
    )
    if share is None:
        msg = "Cohort post not found."
        raise PermissionDenied(msg)
    if share.assignment_group_id not in _visible_group_ids(viewer):
        msg = "You do not have access to this cohort post."
        raise PermissionDenied(msg)
    return share


class ShareReactView(APIView):
    """Toggle the caller's like on a post. Self-likes are refused."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["post", "head", "options"]

    def post(self, request, share_id: int, *args, **kwargs):
        viewer = viewer_or_403(request)
        share = _share_or_403(viewer, share_id)
        if share.person_id == viewer.person.id:
            msg = "You cannot like your own post."
            raise PermissionDenied(msg)

        existing = ShareReaction.all_objects.filter(
            cohort_share=share, person=viewer.person, kind=ShareReaction.KIND_LIKE,
        ).first()
        if existing is not None:
            existing.delete()
            liked = False
        else:
            ShareReaction.all_objects.create(
                cohort_share=share,
                person=viewer.person,
                kind=ShareReaction.KIND_LIKE,
            )
            liked = True

        return Response({
            "id": share.id,
            "liked_by_me": liked,
            "like_count": ShareReaction.all_objects.filter(cohort_share=share).count(),
        })


class ShareHideView(APIView):
    """Director moderation: hide or un-hide a post, logging who and when."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["post", "head", "options"]

    def post(self, request, share_id: int, *args, **kwargs):
        viewer = viewer_or_403(request)
        if not viewer.is_admin:
            msg = "Only a Director may moderate the cohort feed."
            raise PermissionDenied(msg)
        share = _share_or_403(viewer, share_id)

        ser = ShareHideSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        is_hidden = ser.validated_data["is_hidden"]

        if share.is_hidden != is_hidden:
            share.is_hidden = is_hidden
            share.save(update_fields=["is_hidden"])
            CohortShareModeration.all_objects.create(
                cohort_share=share,
                actor=viewer.person,
                action=(
                    CohortShareModeration.ACTION_HIDE
                    if is_hidden
                    else CohortShareModeration.ACTION_UNHIDE
                ),
            )
        return Response(
            {"id": share.id, "is_hidden": share.is_hidden},
            status=status.HTTP_200_OK,
        )
