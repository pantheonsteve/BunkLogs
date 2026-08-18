"""Shared entry-thread endpoints — Step 4_9 §3.

GET  /api/v1/threads/                  — list, filterable into the role queues
GET  /api/v1/threads/<id>/             — full message list
POST /api/v1/threads/<id>/messages/    — reply or self-update
POST /api/v1/threads/<id>/read/        — upsert the read cursor
POST /api/v1/threads/<id>/resolve/     — faculty/director close-out

All three homepages read from here. Queue ordering is oldest-first because
the failure mode this surface exists to prevent is a teenager's entry going
unanswered for three weeks.
"""

from __future__ import annotations

from django.db.models import Count
from django.utils import timezone
from rest_framework import serializers
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.models import EntryThread
from bunk_logs.core.models import ThreadMessage
from bunk_logs.core.models import ThreadRead
from bunk_logs.core.reflection_threads import unread_thread_ids

from .common import ThreadViewer
from .common import can_post_to_thread
from .common import can_read_thread
from .common import can_resolve_thread
from .common import message_payload
from .common import readable_threads_qs
from .common import thread_detail
from .common import thread_list_item
from .common import viewer_or_403

TRUE_VALUES = {"1", "true", "True", "yes"}


class ThreadsPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class ThreadMessageCreateSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=10000)

    def validate_body(self, value: str) -> str:
        body = value.strip()
        if not body:
            msg = "Message body cannot be empty."
            raise serializers.ValidationError(msg)
        return body


def _thread_or_403(viewer: ThreadViewer, thread_id: int) -> EntryThread:
    """Fetch a thread the viewer may read.

    A thread they may not read is a 403 rather than a 404 only after the
    org check has already passed -- cross-org ids never resolve at all, so
    nothing leaks about another tenant's data.
    """
    thread = (
        EntryThread.objects.filter(id=thread_id)
        .select_related(
            "subject_person",
            "reflection",
            "reflection__template",
            "cohort_share",
            "cohort_share__person",
        )
        .first()
    )
    if thread is None:
        msg = "Thread not found."
        raise PermissionDenied(msg)
    if not can_read_thread(viewer, thread):
        msg = "You do not have access to this thread."
        raise PermissionDenied(msg)
    return thread


def _mark_read(person, thread: EntryThread) -> None:
    ThreadRead.all_objects.update_or_create(
        thread=thread, person=person, defaults={"last_read_at": timezone.now()},
    )


class ThreadListView(APIView):
    """Threads the caller may read, filtered into whichever queue they need.

    Filters: ``routes_to``, ``resolved``, ``subject_person``,
    ``assignment_group``, ``unread``, ``field_key``. Ordering defaults to
    oldest-first for routed queues and newest-activity-first otherwise.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        viewer = viewer_or_403(request)
        qs = readable_threads_qs(viewer)

        params = request.query_params
        routes_to = (params.get("routes_to") or "").strip()
        if routes_to:
            # "faculty" and "director" both include entries routed to
            # "both", otherwise a shared item would sit in neither queue.
            qs = qs.filter(routes_to__in=[routes_to, EntryThread.ROUTES_TO_BOTH])

        resolved = (params.get("resolved") or "").strip()
        if resolved:
            qs = qs.filter(resolved_at__isnull=resolved not in TRUE_VALUES)

        subject_person = (params.get("subject_person") or "").strip()
        if subject_person.isdigit():
            qs = qs.filter(subject_person_id=int(subject_person))

        field_key = (params.get("field_key") or "").strip()
        if field_key:
            qs = qs.filter(field_key=field_key)

        assignment_group = (params.get("assignment_group") or "").strip()
        if assignment_group.isdigit():
            qs = qs.filter(cohort_share__assignment_group_id=int(assignment_group))

        qs = qs.annotate(message_count=Count("messages", distinct=True))
        qs = qs.order_by("created_at") if routes_to else qs.order_by(
            "-last_message_at", "-created_at",
        )

        unread_only = (params.get("unread") or "").strip() in TRUE_VALUES
        if unread_only:
            qs = qs.filter(id__in=unread_thread_ids(viewer.person))

        paginator = ThreadsPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        threads = list(page)
        unread = unread_thread_ids(viewer.person, [t.id for t in threads])
        last_messages = _last_message_by_thread([t.id for t in threads])

        return paginator.get_paginated_response([
            thread_list_item(
                thread,
                unread=thread.id in unread,
                message_count=thread.message_count,
                last_message=last_messages.get(thread.id),
                today=viewer.today,
            )
            for thread in threads
        ])


def _last_message_by_thread(thread_ids: list[int]) -> dict[int, ThreadMessage]:
    """Latest message per thread in one query, for list previews."""
    if not thread_ids:
        return {}
    latest: dict[int, ThreadMessage] = {}
    for message in ThreadMessage.all_objects.filter(
        thread_id__in=thread_ids,
    ).order_by("thread_id", "created_at"):
        latest[message.thread_id] = message
    return latest


class ThreadDetailView(APIView):
    """Full thread with its messages in chronological order.

    Opening a thread marks it read, so the caller does not have to make a
    second request to clear the indicator.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, thread_id: int, *args, **kwargs):
        viewer = viewer_or_403(request)
        thread = _thread_or_403(viewer, thread_id)
        messages = list(
            ThreadMessage.all_objects.filter(thread=thread)
            .select_related("author")
            .order_by("created_at"),
        )
        _mark_read(viewer.person, thread)
        return Response(thread_detail(thread, messages, viewer))


class ThreadMessageCreateView(APIView):
    """Post a reply or a self-update onto a thread."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["post", "head", "options"]

    def post(self, request, thread_id: int, *args, **kwargs):
        viewer = viewer_or_403(request)
        thread = _thread_or_403(viewer, thread_id)
        if not can_post_to_thread(viewer, thread):
            msg = "You cannot post to this thread."
            raise PermissionDenied(msg)

        ser = ThreadMessageCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        message = ThreadMessage.all_objects.create(
            thread=thread,
            author=viewer.person,
            author_role_at_write=viewer.role_label(),
            body=ser.validated_data["body"],
        )
        thread.last_message_at = message.created_at
        thread.save(update_fields=["last_message_at"])
        # Writing counts as reading: a replier should not badge their own row.
        _mark_read(viewer.person, thread)

        return Response(
            message_payload(message, thread), status=status.HTTP_201_CREATED,
        )


class ThreadReadView(APIView):
    """Upsert the caller's read cursor on a thread."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["post", "head", "options"]

    def post(self, request, thread_id: int, *args, **kwargs):
        viewer = viewer_or_403(request)
        thread = _thread_or_403(viewer, thread_id)
        _mark_read(viewer.person, thread)
        return Response({"id": thread.id, "unread": False})


class ThreadResolveView(APIView):
    """Close out a routed thread.

    Replying and resolving are separate actions: a question can need
    follow-up, so answering it must not silently take it off the list.
    """

    permission_classes = [IsAuthenticated]
    http_method_names = ["post", "head", "options"]

    def post(self, request, thread_id: int, *args, **kwargs):
        viewer = viewer_or_403(request)
        thread = _thread_or_403(viewer, thread_id)
        if not can_resolve_thread(viewer, thread):
            msg = "You cannot resolve this thread."
            raise PermissionDenied(msg)
        if thread.resolved_at is None:
            thread.resolved_at = timezone.now()
            thread.save(update_fields=["resolved_at"])
        return Response({
            "id": thread.id,
            "resolved_at": thread.resolved_at.isoformat(),
        })
