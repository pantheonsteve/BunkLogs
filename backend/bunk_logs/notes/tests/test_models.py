"""Model tests for the Notes platform (Step 7_19).

Covers creation, constraints, FK cascade behavior, and unique_together.
"""

from __future__ import annotations

import pytest

from bunk_logs.notes.models import Note
from bunk_logs.notes.models import NoteArchive
from bunk_logs.notes.models import NoteAudienceCapture
from bunk_logs.notes.models import NoteReadReceipt
from bunk_logs.notes.models import NoteReply

pytestmark = pytest.mark.django_db


def _note(org, program, author, **kwargs):
    return Note.all_objects.create(
        organization=org,
        program=program,
        author=author,
        author_role_at_write=kwargs.pop("author_role_at_write", "counselor"),
        subject=kwargs.pop("subject", "Test subject"),
        body=kwargs.pop("body", "Test body"),
        **kwargs,
    )


class TestNoteModel:
    def test_create(self, org, program, counselor_person):
        note = _note(org, program, counselor_person)
        assert note.pk is not None
        assert note.subject == "Test subject"

    def test_str(self, org, program, counselor_person):
        note = _note(org, program, counselor_person)
        assert f"Note({note.id})" in str(note)

    def test_source_type_blank_by_default(self, org, program, counselor_person):
        note = _note(org, program, counselor_person)
        assert note.source_content_type == ""
        assert note.source_object_id == ""

    def test_source_type_choices(self, org, program, counselor_person):
        note = _note(
            org, program, counselor_person,
            source_content_type="reflection_concern",
            source_object_id="42",
        )
        assert note.source_content_type == "reflection_concern"


class TestNoteAudienceCapture:
    def test_create(self, org, program, counselor_person, uh_person):
        note = _note(org, program, counselor_person)
        cap = NoteAudienceCapture.objects.create(
            note=note, person=uh_person, option_key="my_unit_head",
        )
        assert cap.pk is not None

    def test_cascade_delete_with_note(self, org, program, counselor_person, uh_person):
        note = _note(org, program, counselor_person)
        NoteAudienceCapture.objects.create(
            note=note, person=uh_person, option_key="my_unit_head",
        )
        note_id = note.id
        note.delete()
        assert NoteAudienceCapture.objects.filter(note_id=note_id).count() == 0


class TestNoteReply:
    def test_create(self, org, program, counselor_person, uh_person):
        note = _note(org, program, counselor_person)
        reply = NoteReply.objects.create(
            note=note, author=uh_person, author_role_at_write="unit_head", body="Hello",
        )
        assert reply.pk is not None
        assert reply.note_id == note.id

    def test_ordering_chronological(self, org, program, counselor_person, uh_person):
        note = _note(org, program, counselor_person)
        r1 = NoteReply.objects.create(note=note, author=uh_person, author_role_at_write="unit_head", body="First")
        r2 = NoteReply.objects.create(note=note, author=uh_person, author_role_at_write="unit_head", body="Second")
        replies = list(note.replies.all())
        assert replies[0].id == r1.id
        assert replies[1].id == r2.id


class TestNoteReadReceipt:
    def test_upsert_semantics(self, org, program, counselor_person, uh_person):
        from django.utils import timezone
        note = _note(org, program, counselor_person)
        now = timezone.now()
        r, _ = NoteReadReceipt.objects.update_or_create(
            note=note, person=uh_person,
            defaults={"last_read_at": now, "last_read_entry_id": str(note.id)},
        )
        # Update again — still only one row
        NoteReadReceipt.objects.update_or_create(
            note=note, person=uh_person,
            defaults={"last_read_at": now, "last_read_entry_id": str(note.id)},
        )
        assert NoteReadReceipt.objects.filter(note=note, person=uh_person).count() == 1

    def test_unique_together(self, org, program, counselor_person, uh_person):
        from django.db import IntegrityError
        from django.utils import timezone
        note = _note(org, program, counselor_person)
        now = timezone.now()
        NoteReadReceipt.objects.create(
            note=note, person=uh_person, last_read_at=now, last_read_entry_id="1",
        )
        with pytest.raises(IntegrityError):
            NoteReadReceipt.objects.create(
                note=note, person=uh_person, last_read_at=now, last_read_entry_id="1",
            )


class TestNoteArchive:
    def test_archive_unique(self, org, program, counselor_person, uh_person):
        from django.db import IntegrityError
        note = _note(org, program, counselor_person)
        NoteArchive.objects.create(note=note, person=uh_person)
        with pytest.raises(IntegrityError):
            NoteArchive.objects.create(note=note, person=uh_person)

    def test_get_or_create_idempotent(self, org, program, counselor_person, uh_person):
        note = _note(org, program, counselor_person)
        a1, created1 = NoteArchive.objects.get_or_create(note=note, person=uh_person)
        a2, created2 = NoteArchive.objects.get_or_create(note=note, person=uh_person)
        assert created1 is True
        assert created2 is False
        assert a1.pk == a2.pk
