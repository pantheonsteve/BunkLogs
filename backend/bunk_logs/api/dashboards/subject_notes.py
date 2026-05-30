"""SubjectNote API endpoints.

POST   /api/v1/subjects/{person_id}/notes/
GET    /api/v1/subjects/{person_id}/notes/
POST   /api/v1/subjects/{person_id}/notes/{note_id}/amend/

Notes are immutable after creation; corrections are appended as amendments
via ``amendment_of``. Visibility is a four-level enum enforced at read time.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.models import Person
from bunk_logs.core.models import SubjectNote
from bunk_logs.core.permissions.subject_note_authoring import can_author_subject_note
from bunk_logs.core.permissions.subject_note_read import filter_subject_notes_readable
from bunk_logs.core.permissions.super_admin import is_super_admin

from .subject import _can_view_subject_dashboard
from .subject import _viewer_capability

User = get_user_model()


# Visibility filter — delegated to core.permissions.subject_note_read


def _notes_visible_to(viewer_person: Person | None, notes_qs, org, user, subject: Person):
    """Filter SubjectNote queryset to rows the viewer is allowed to read."""
    return filter_subject_notes_readable(
        notes_qs,
        viewer_person,
        org,
        user,
        subject=subject,
    )


# ---------------------------------------------------------------------------
# Serializer helpers
# ---------------------------------------------------------------------------

def _serialize_note(note: SubjectNote) -> dict:
    return {
        "id": note.id,
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


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

class SubjectNoteListCreateView(APIView):
    """GET/POST notes for a single subject."""

    permission_classes = [IsAuthenticated]

    def _resolve(self, request, person_id: int):
        org = getattr(request, "organization", None)
        if org is None:
            return None, None, Response({"detail": "Organization context required."}, status=403)

        subject = Person.objects.filter(id=person_id).first()
        if subject is None or subject.organization_id != org.id:
            return None, None, Response({"detail": "Subject not found."}, status=404)

        viewer_person = Person.all_objects.filter(user=request.user).first()
        if not _can_view_subject_dashboard(viewer_person, subject, org, request.user):
            return None, None, Response(
                {"detail": "You do not have permission to access this subject's notes."},
                status=403,
            )
        return org, subject, None

    def get(self, request, person_id: int, *args, **kwargs):
        org, subject, err = self._resolve(request, person_id)
        if err:
            return err

        viewer_person = Person.all_objects.filter(user=request.user).first()
        notes_qs = (
            SubjectNote.objects.filter(subject=subject)
            .select_related("author_person")
            .order_by("-created_at")
        )
        visible = _notes_visible_to(viewer_person, notes_qs, org, request.user, subject)
        return Response({"notes": [_serialize_note(n) for n in visible]})

    def post(self, request, person_id: int, *args, **kwargs):
        org, subject, err = self._resolve(request, person_id)
        if err:
            return err

        viewer_person = Person.all_objects.filter(user=request.user).first()
        if not can_author_subject_note(viewer_person, subject, org, request.user):
            return Response(
                {"detail": "You do not have permission to write notes about this subject."},
                status=403,
            )

        data = request.data
        body = (data.get("body") or "").strip()
        if not body:
            return Response({"detail": "body is required."}, status=400)

        visibility = data.get("visibility", SubjectNote.Visibility.SUPERVISORS_ONLY)
        if visibility not in SubjectNote.Visibility.values:
            return Response(
                {"detail": f"visibility must be one of {SubjectNote.Visibility.values}"},
                status=400,
            )

        # Resolve program: pick the first active program this subject belongs to in the org
        from bunk_logs.core.models import Membership
        program = (
            Membership.all_objects.filter(
                person=subject, is_active=True, program__organization=org,
            )
            .select_related("program")
            .values_list("program", flat=True)
            .first()
        )
        if program is None:
            # Fall back to any active program in the org
            from bunk_logs.core.models import Program
            program = Program.all_objects.filter(
                organization=org, is_active=True,
            ).values_list("id", flat=True).first()
        if program is None:
            return Response({"detail": "No active program found for this organization."}, status=400)

        note = SubjectNote.all_objects.create(
            organization=org,
            program_id=program,
            subject=subject,
            author_person=viewer_person,
            submitted_by=request.user,
            context=(data.get("context") or "").strip()[:64],
            body=body,
            visibility=visibility,
            is_sensitive=bool(data.get("is_sensitive", False)),
            subject_visible=bool(data.get("subject_visible", False)),
        )
        return Response(_serialize_note(note), status=201)


class SubjectNoteAmendView(APIView):
    """POST an amendment to an existing immutable note."""

    permission_classes = [IsAuthenticated]

    def post(self, request, person_id: int, note_id: int, *args, **kwargs):
        org = getattr(request, "organization", None)
        if org is None:
            return Response({"detail": "Organization context required."}, status=403)

        subject = Person.objects.filter(id=person_id).first()
        if subject is None or subject.organization_id != org.id:
            return Response({"detail": "Subject not found."}, status=404)

        original = SubjectNote.objects.filter(id=note_id, subject=subject).first()
        if original is None:
            return Response({"detail": "Note not found."}, status=404)

        # Only the original author or an admin/program_lead may amend
        viewer_person = Person.all_objects.filter(user=request.user).first()
        cap = _viewer_capability(viewer_person, org) if viewer_person else None
        is_author = viewer_person and viewer_person.id == original.author_person_id
        if not is_author and cap not in ("admin", "program_lead") and not is_super_admin(request.user):
            return Response({"detail": "Only the note author may add amendments."}, status=403)

        body = (request.data.get("body") or "").strip()
        if not body:
            return Response({"detail": "body is required."}, status=400)

        amendment = SubjectNote.all_objects.create(
            organization=org,
            program=original.program,
            subject=subject,
            author_person=viewer_person,
            submitted_by=request.user,
            amendment_of=original,
            context=original.context,
            body=body,
            visibility=original.visibility,
            is_sensitive=original.is_sensitive,
            subject_visible=original.subject_visible,
        )
        return Response(_serialize_note(amendment), status=201)
