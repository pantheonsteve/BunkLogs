"""Cross-subject feed and subject-search endpoints for the global Subject Notes UX.

GET  /api/v1/subject-notes/recent/?limit=50
GET  /api/v1/subject-notes/subjects/?q=<query>&limit=25

Visibility logic is centralized in ``core.permissions.subject_note_read``:
capability-based read access, supervisor-via-group-authorship, and authors
always see notes they wrote.
"""

from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.models import Person
from bunk_logs.core.models import SubjectNote
from bunk_logs.core.permissions.subject_note_authoring import authorable_subject_queryset
from bunk_logs.core.permissions.subject_note_read import filter_subject_notes_readable
from bunk_logs.core.permissions.super_admin import is_super_admin

User = get_user_model()

DEFAULT_RECENT_LIMIT = 50
MAX_RECENT_LIMIT = 200
DEFAULT_SEARCH_LIMIT = 25
MAX_SEARCH_LIMIT = 100


def _serialize_note(note: SubjectNote) -> dict[str, Any]:
    return {
        "id": note.id,
        "subject": (
            {"id": note.subject_id, "full_name": note.subject.full_name}
            if note.subject_id and note.subject else None
        ),
        "body": note.body,
        "context": note.context,
        "visibility": note.visibility,
        "is_sensitive": note.is_sensitive,
        "subject_visible": note.subject_visible,
        "amendment_of": note.amendment_of_id,
        "author": (
            {"id": note.author_person_id, "name": note.author_person.full_name}
            if note.author_person_id and note.author_person else None
        ),
        "created_at": note.created_at.isoformat() if note.created_at else None,
    }


class RecentSubjectNotesView(APIView):
    """GET /api/v1/subject-notes/recent/ — most recent SubjectNotes the viewer can see."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        org = getattr(request, "organization", None)
        if org is None:
            return Response({"detail": "Organization context required."}, status=403)

        try:
            limit = int(request.query_params.get("limit", DEFAULT_RECENT_LIMIT))
        except (TypeError, ValueError):
            limit = DEFAULT_RECENT_LIMIT
        limit = max(1, min(limit, MAX_RECENT_LIMIT))

        viewer_person = Person.all_objects.filter(user=request.user).first()
        qs = (
            SubjectNote.all_objects.filter(organization=org)
            .select_related("author_person", "subject")
            .order_by("-created_at")
        )

        notes = list(
            filter_subject_notes_readable(
                qs,
                viewer_person,
                org,
                request.user,
            )[:limit],
        )

        return Response({"notes": [_serialize_note(n) for n in notes]})


class SearchableSubjectsView(APIView):
    """GET /api/v1/subject-notes/subjects/?q= — Persons the viewer may write notes about.

    Uses ``authorable_subject_queryset`` (org role defaults + membership overrides),
    not capability alone.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        org = getattr(request, "organization", None)
        if org is None:
            return Response({"detail": "Organization context required."}, status=403)

        q = (request.query_params.get("q") or "").strip()
        try:
            limit = int(request.query_params.get("limit", DEFAULT_SEARCH_LIMIT))
        except (TypeError, ValueError):
            limit = DEFAULT_SEARCH_LIMIT
        limit = max(1, min(limit, MAX_SEARCH_LIMIT))

        viewer_person = Person.all_objects.filter(user=request.user).first()

        if is_super_admin(request.user):
            base = Person.all_objects.filter(organization=org)
        elif viewer_person is None:
            base = Person.all_objects.none()
        else:
            base = authorable_subject_queryset(viewer_person, org)

        if q:
            base = base.filter(
                Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(preferred_name__icontains=q),
            )
        persons = list(base.order_by("last_name", "first_name")[:limit])

        return Response({
            "subjects": [
                {"id": p.id, "full_name": p.full_name}
                for p in persons
            ],
        })


__all__ = [
    "RecentSubjectNotesView",
    "SearchableSubjectsView",
]
