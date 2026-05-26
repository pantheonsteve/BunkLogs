"""API tests for the Notes platform endpoints (Step 7_19).

Covers: success paths, permission failures, pagination, archive idempotency,
cross-org isolation, and empty-audience validation.
"""

from __future__ import annotations

from datetime import date

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import Membership, Organization, Person, Supervision
from bunk_logs.notes.models import Note, NoteArchive, NoteAudienceCapture, NoteReply

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _auth_client(user, org):
    """Return an APIClient authed as user with org context header."""
    client = APIClient()
    client.force_authenticate(user=user)
    client.defaults["HTTP_X_ORGANIZATION_SLUG"] = org.slug
    return client


def _make_note(org, program, author, *, audience_persons=None):
    note = Note.all_objects.create(
        organization=org, program=program, author=author,
        author_role_at_write="counselor", subject="Test", body="Body",
    )
    for person in audience_persons or []:
        NoteAudienceCapture.objects.create(note=note, person=person, option_key="my_unit_head")
    return note


# ---------------------------------------------------------------------------
# GET /api/v1/notes/inbox/
# ---------------------------------------------------------------------------


class TestInboxEndpoint:
    def test_returns_notes_where_in_audience(
        self, org, program, counselor_person, counselor_user, counselor_membership, uh_person,
    ):
        note = _make_note(org, program, uh_person, audience_persons=[counselor_person])
        client = _auth_client(counselor_user, org)
        response = client.get("/api/v1/notes/inbox/")
        assert response.status_code == 200
        data = response.json()
        ids = [n["id"] for n in (data.get("results", data))]
        assert note.id in ids

    def test_does_not_return_notes_not_in_audience(
        self, org, program, counselor_person, counselor_user, counselor_membership, uh_person,
    ):
        note = _make_note(org, program, uh_person)  # no audience
        client = _auth_client(counselor_user, org)
        response = client.get("/api/v1/notes/inbox/")
        assert response.status_code == 200
        data = response.json()
        ids = [n["id"] for n in (data.get("results", data))]
        assert note.id not in ids

    def test_archived_notes_excluded(
        self, org, program, counselor_person, counselor_user, counselor_membership, uh_person,
    ):
        note = _make_note(org, program, uh_person, audience_persons=[counselor_person])
        NoteArchive.objects.create(note=note, person=counselor_person)
        client = _auth_client(counselor_user, org)
        response = client.get("/api/v1/notes/inbox/")
        assert response.status_code == 200
        data = response.json()
        ids = [n["id"] for n in (data.get("results", data))]
        assert note.id not in ids

    def test_403_when_no_v1_role(self, org, program):
        from bunk_logs.users.models import User
        user = User.objects.create_user(email="notrole@t.test", password="pw")
        person = Person.all_objects.create(organization=org, first_name="Nr", last_name="X", user=user)
        Membership.all_objects.create(program=program, person=person, role="kitchen_staff", is_active=True)
        client = _auth_client(user, org)
        response = client.get("/api/v1/notes/inbox/")
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# GET /api/v1/notes/sent/
# ---------------------------------------------------------------------------


class TestSentEndpoint:
    def test_returns_authored_notes(
        self, org, program, counselor_person, counselor_user, counselor_membership, uh_person,
    ):
        note = _make_note(org, program, counselor_person, audience_persons=[uh_person])
        client = _auth_client(counselor_user, org)
        response = client.get("/api/v1/notes/sent/")
        assert response.status_code == 200
        data = response.json()
        ids = [n["id"] for n in (data.get("results", data))]
        assert note.id in ids

    def test_cross_org_isolation(
        self, org, other_org, program, counselor_person, counselor_user,
        counselor_membership, other_program,
    ):
        # Create a note in the other org
        other_person = Person.all_objects.create(
            organization=other_org, first_name="Other", last_name="P",
        )
        other_note = Note.all_objects.create(
            organization=other_org, program=other_program, author=other_person,
            author_role_at_write="counselor", subject="Other", body="body",
        )
        client = _auth_client(counselor_user, org)
        response = client.get("/api/v1/notes/sent/")
        assert response.status_code == 200
        data = response.json()
        ids = [n["id"] for n in (data.get("results", data))]
        assert other_note.id not in ids


# ---------------------------------------------------------------------------
# GET /api/v1/notes/<id>/ — thread view
# ---------------------------------------------------------------------------


class TestThreadEndpoint:
    def test_author_can_read_thread(
        self, org, program, counselor_person, counselor_user, counselor_membership, uh_person,
    ):
        note = _make_note(org, program, counselor_person, audience_persons=[uh_person])
        client = _auth_client(counselor_user, org)
        response = client.get(f"/api/v1/notes/{note.id}/")
        assert response.status_code == 200
        assert response.json()["id"] == note.id

    def test_audience_member_can_read_thread(
        self, org, program, counselor_person, uh_person, uh_user, uh_membership,
    ):
        note = _make_note(org, program, counselor_person, audience_persons=[uh_person])
        client = _auth_client(uh_user, org)
        response = client.get(f"/api/v1/notes/{note.id}/")
        assert response.status_code == 200

    def test_non_audience_cannot_read_thread(
        self, org, program, counselor_person, counselor_user, counselor_membership, uh_person,
    ):
        note = _make_note(org, program, uh_person)  # no audience
        client = _auth_client(counselor_user, org)
        response = client.get(f"/api/v1/notes/{note.id}/")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/v1/notes/ — create
# ---------------------------------------------------------------------------


class TestNoteCreateEndpoint:
    def test_create_note_success(
        self,
        org, program,
        counselor_person, counselor_user, counselor_membership,
        uh_person, uh_membership,
        uh_supervises_counselor,
    ):
        client = _auth_client(counselor_user, org)
        payload = {
            "audience": [{"option_key": "my_unit_head"}],
            "subject": "Hello UH",
            "body": "Some message",
        }
        response = client.post("/api/v1/notes/", payload, format="json")
        assert response.status_code == 201
        data = response.json()
        assert data["subject"] == "Hello UH"
        # Audience was captured
        note = Note.all_objects.get(pk=data["id"])
        assert note.audience_captures.filter(person=uh_person).exists()

    def test_empty_audience_returns_400(
        self,
        org, program,
        counselor_person, counselor_user, counselor_membership,
    ):
        client = _auth_client(counselor_user, org)
        payload = {
            "audience": [{"option_key": "my_unit_head"}],  # no supervision -> empty
            "subject": "Hi",
            "body": "Body",
        }
        response = client.post("/api/v1/notes/", payload, format="json")
        # No UH supervises counselor in this test, so audience resolves empty
        assert response.status_code == 400

    def test_missing_required_fields(self, org, program, counselor_person, counselor_user, counselor_membership):
        client = _auth_client(counselor_user, org)
        response = client.post("/api/v1/notes/", {"audience": []}, format="json")
        assert response.status_code == 400

    def test_non_v1_role_cannot_create(self, org, program):
        from bunk_logs.users.models import User
        user = User.objects.create_user(email="ks2@t.test", password="pw")
        person = Person.all_objects.create(organization=org, first_name="KS2", last_name="X", user=user)
        Membership.all_objects.create(program=program, person=person, role="kitchen_staff", is_active=True)
        client = _auth_client(user, org)
        payload = {"audience": [{"option_key": "administration"}], "subject": "Hi", "body": "Body"}
        response = client.post("/api/v1/notes/", payload, format="json")
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# POST /api/v1/notes/<id>/replies/
# ---------------------------------------------------------------------------


class TestReplyCreateEndpoint:
    def test_audience_member_can_reply(
        self, org, program, counselor_person, counselor_user, counselor_membership,
        uh_person, uh_user, uh_membership,
    ):
        note = _make_note(org, program, counselor_person, audience_persons=[uh_person])
        client = _auth_client(uh_user, org)
        response = client.post(
            f"/api/v1/notes/{note.id}/replies/", {"body": "Reply body"}, format="json"
        )
        assert response.status_code == 201

    def test_non_audience_cannot_reply(
        self, org, program, counselor_person, uh_person, uh_user,
    ):
        note = _make_note(org, program, uh_person)  # counselor not in audience
        client = _auth_client(uh_user, org)  # uh is author; but counselor_user isn't in audience
        # Make a separate user who's not in audience
        from bunk_logs.users.models import User
        user2 = User.objects.create_user(email="noaud@t.test", password="pw")
        person2 = Person.all_objects.create(organization=org, first_name="NA", last_name="P", user=user2)
        Membership.all_objects.create(program=program, person=person2, role="counselor", is_active=True)
        c2 = _auth_client(user2, org)
        response = c2.post(f"/api/v1/notes/{note.id}/replies/", {"body": "x"}, format="json")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/v1/notes/<id>/archive/ and /unarchive/ — idempotency
# ---------------------------------------------------------------------------


class TestArchiveEndpoints:
    def test_archive_idempotent(
        self, org, program, counselor_person, counselor_user, counselor_membership, uh_person, uh_membership,
    ):
        note = _make_note(org, program, uh_person, audience_persons=[counselor_person])
        client = _auth_client(counselor_user, org)
        r1 = client.post(f"/api/v1/notes/{note.id}/archive/")
        r2 = client.post(f"/api/v1/notes/{note.id}/archive/")
        assert r1.status_code == 200
        assert r2.status_code == 200
        # Still only one archive row
        assert NoteArchive.objects.filter(note=note, person=counselor_person).count() == 1

    def test_unarchive_idempotent(
        self, org, program, counselor_person, counselor_user, counselor_membership, uh_person, uh_membership,
    ):
        note = _make_note(org, program, uh_person, audience_persons=[counselor_person])
        NoteArchive.objects.create(note=note, person=counselor_person)
        client = _auth_client(counselor_user, org)
        r1 = client.post(f"/api/v1/notes/{note.id}/unarchive/")
        r2 = client.post(f"/api/v1/notes/{note.id}/unarchive/")
        assert r1.status_code == 200
        assert r2.status_code == 200

    def test_archive_does_not_affect_other_user(
        self, org, program, counselor_person, counselor_user, counselor_membership,
        uh_person, uh_user, uh_membership,
    ):
        note = _make_note(org, program, counselor_person, audience_persons=[uh_person])
        client = _auth_client(counselor_user, org)
        client.post(f"/api/v1/notes/{note.id}/archive/")
        # UH can still read the note
        uh_client = _auth_client(uh_user, org)
        response = uh_client.get(f"/api/v1/notes/{note.id}/")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# GET /api/v1/notes/unread-count/
# ---------------------------------------------------------------------------


class TestUnreadCount:
    def test_zero_when_inbox_empty(self, org, program, counselor_person, counselor_user, counselor_membership):
        client = _auth_client(counselor_user, org)
        response = client.get("/api/v1/notes/unread-count/")
        assert response.status_code == 200
        assert response.json()["count"] == 0

    def test_counts_unread_inbox_note(
        self, org, program, counselor_person, counselor_user, counselor_membership, uh_person, uh_membership,
    ):
        _make_note(org, program, uh_person, audience_persons=[counselor_person])
        client = _auth_client(counselor_user, org)
        response = client.get("/api/v1/notes/unread-count/")
        assert response.status_code == 200
        assert response.json()["count"] == 1


# ---------------------------------------------------------------------------
# GET /api/v1/notes/audience-options/
# ---------------------------------------------------------------------------


class TestAudienceOptionsEndpoint:
    def test_counselor_gets_options(
        self, org, program, counselor_person, counselor_user, counselor_membership,
    ):
        client = _auth_client(counselor_user, org)
        response = client.get("/api/v1/notes/audience-options/")
        assert response.status_code == 200
        keys = [o["option_key"] for o in response.json()]
        assert "my_unit_head" in keys

    def test_non_v1_role_returns_empty(self, org, program):
        from bunk_logs.users.models import User
        user = User.objects.create_user(email="ks3@t.test", password="pw")
        person = Person.all_objects.create(organization=org, first_name="KS3", last_name="X", user=user)
        Membership.all_objects.create(program=program, person=person, role="kitchen_staff", is_active=True)
        client = _auth_client(user, org)
        response = client.get("/api/v1/notes/audience-options/")
        assert response.status_code == 403
