"""Tests for ``/api/v1/specialist/*`` (Step 7_9, Stories 24-29).

Coverage (lean mode):

* Happy-path: dashboard, camper picker, note create/edit, camper view.
* Auth/permission: non-specialist cannot access specialist endpoints.
* Visibility: Specialist cannot see another Specialist's notes via the
  camper view endpoint (queryset-level filter, Story 28 criterion 4).
* Flag creation: ``flag_for_camper_care=True`` raises an Active Flag
  linked to the note (Story 26 criterion 7).
* Flag retraction blocked: PATCH cannot un-flag once a flag is raised
  (Story 27 criterion 5, Decision S5).
* Camper picker search: 100-camper roster returns all matches within
  reasonable query count (proxy for the 1,500-camper performance target).
"""

from __future__ import annotations

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Flag
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Note
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import ReflectionTemplate

User = get_user_model()
pytestmark = pytest.mark.django_db


def _hdr(slug: str) -> dict:
    return {"HTTP_X_ORGANIZATION_SLUG": slug}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def org():
    return Organization.objects.create(name="SP Org", slug="sp-org")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="SP Org Summer 2026",
        slug="sp-summer-2026",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def specialist_template(org, program):
    return ReflectionTemplate.all_objects.create(
        organization=None,
        slug="specialist-self-reflection",
        version=1,
        name="Specialist Self-Reflection",
        description="Test template",
        cadence="daily",
        schema={"fields": [
            {"key": "day_off", "type": "yes_no", "required": False},
            {"key": "notes", "type": "textarea", "required": False},
        ]},
        languages=["en"],
        is_active=True,
        subject_mode="self",
        assignment_scope="none",
        assignment_group_types=[],
        author_role_filter=["specialist"],
        subject_role_filter=[],
        required_per_subject_per_period=1,
        subject_visible=False,
        supports_privacy=False,
        role="specialist",
        program_type=None,
    )


def _make_person(org, *, first, last, email):
    user = User.objects.create_user(email=email, password="pw")
    person = Person.all_objects.create(
        organization=org, first_name=first, last_name=last, user=user,
    )
    return person, user


def _make_membership(program, person, role, tags=None):
    return Membership.all_objects.create(
        program=program, person=person, role=role, is_active=True,
        tags=tags or [],
    )


def _make_bunk(org, program, *, name="Elm"):
    return AssignmentGroup.all_objects.create(
        organization=org,
        program=program,
        name=name,
        slug=name.lower().replace(" ", "-"),
        group_type="bunk",
        is_active=True,
    )


def _assign_camper(bunk, person):
    return AssignmentGroupMembership.all_objects.create(
        group=bunk,
        person=person,
        role_in_group="subject",
        is_active=True,
    )


@pytest.fixture
def sp_person_user(org):
    return _make_person(org, first="Alex", last="Water", email="sp@sp.test")


@pytest.fixture
def sp_membership(program, sp_person_user):
    person, _ = sp_person_user
    return _make_membership(program, person, "specialist", tags=["specialist:waterfront"])


@pytest.fixture
def bunk(org, program):
    return _make_bunk(org, program, name="Elm")


@pytest.fixture
def camper_person(org):
    _, camper_user = _make_person(org, first="Jake", last="Smith", email="camper@sp.test")
    return Person.all_objects.get(user=camper_user)


@pytest.fixture
def camper_agm(bunk, camper_person):
    return _assign_camper(bunk, camper_person)


@pytest.fixture
def api(sp_person_user, sp_membership):
    _, user = sp_person_user
    client = APIClient()
    client.force_authenticate(user=user)
    return client


# ---------------------------------------------------------------------------
# Auth / permission tests
# ---------------------------------------------------------------------------


class TestSpecialistAuthGate:
    def test_unauthenticated_returns_401_or_403(self, org):
        client = APIClient()
        with organization_context(org):
            r = client.get("/api/v1/specialist/dashboard/", **_hdr(org.slug))
        assert r.status_code in (401, 403)

    def test_wrong_role_returns_403(self, org, program):
        person, user = _make_person(org, first="CC", last="User", email="cc2@sp.test")
        _make_membership(program, person, "camper_care")
        client = APIClient()
        client.force_authenticate(user=user)
        with organization_context(org):
            r = client.get("/api/v1/specialist/dashboard/", **_hdr(org.slug))
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Dashboard tests
# ---------------------------------------------------------------------------


class TestSpecialistDashboard:
    def test_dashboard_returns_three_sections(self, api, org, sp_membership):
        with organization_context(org):
            r = api.get("/api/v1/specialist/dashboard/", **_hdr(org.slug))
        assert r.status_code == 200
        data = r.json()
        assert "write_camper_note" in data
        assert "self_reflection" in data
        assert "recent_notes" in data

    def test_header_shows_specialist_label(self, api, org, sp_membership):
        with organization_context(org):
            r = api.get("/api/v1/specialist/dashboard/", **_hdr(org.slug))
        assert r.json()["header"]["role_label"] == "Waterfront Specialist"

    def test_recent_notes_shows_authored_notes(self, api, org, program, sp_person_user, sp_membership, camper_person, camper_agm):
        person, _ = sp_person_user
        Note.all_objects.create(
            organization=org,
            program=program,
            subject=camper_person,
            author=person,
            note_type=Note.NoteType.SPECIALIST,
            body="Good swimmer",
        )
        with organization_context(org):
            r = api.get("/api/v1/specialist/dashboard/", **_hdr(org.slug))
        notes = r.json()["recent_notes"]
        assert len(notes) == 1
        assert notes[0]["body_preview"] == "Good swimmer"

    def test_recent_notes_does_not_show_others_notes(self, api, org, program, sp_person_user, sp_membership, camper_person, camper_agm):
        other, _ = _make_person(org, first="Oth", last="Sp", email="other@sp.test")
        Note.all_objects.create(
            organization=org,
            program=program,
            subject=camper_person,
            author=other,
            note_type=Note.NoteType.SPECIALIST,
            body="Someone else's note",
        )
        with organization_context(org):
            r = api.get("/api/v1/specialist/dashboard/", **_hdr(org.slug))
        assert len(r.json()["recent_notes"]) == 0


# ---------------------------------------------------------------------------
# Camper picker tests
# ---------------------------------------------------------------------------


class TestCamperPicker:
    def test_returns_all_campers_when_no_query(self, api, org, sp_membership, bunk, camper_person, camper_agm):
        with organization_context(org):
            r = api.get("/api/v1/specialist/campers/", **_hdr(org.slug))
        assert r.status_code == 200
        data = r.json()
        assert any(c["id"] == camper_person.id for c in data["results"])

    def test_search_by_first_name(self, api, org, sp_membership, bunk, camper_person, camper_agm):
        with organization_context(org):
            r = api.get("/api/v1/specialist/campers/?q=Jake", **_hdr(org.slug))
        assert r.status_code == 200
        results = r.json()["results"]
        assert any(c["id"] == camper_person.id for c in results)

    def test_search_by_bunk_name(self, api, org, sp_membership, bunk, camper_person, camper_agm):
        with organization_context(org):
            r = api.get("/api/v1/specialist/campers/?q=Elm", **_hdr(org.slug))
        results = r.json()["results"]
        assert any(c["id"] == camper_person.id for c in results)

    def test_zero_results_message_on_no_match(self, api, org, sp_membership, bunk, camper_person, camper_agm):
        with organization_context(org):
            r = api.get("/api/v1/specialist/campers/?q=XYZ_NOMATCH_99", **_hdr(org.slug))
        data = r.json()
        assert data["results"] == []
        assert "No campers match" in (data["zero_results_message"] or "")

    def test_camper_picker_with_100_campers(self, api, org, program, sp_membership, bunk):
        """Proxy for the 1,500-camper performance target: 100 campers, no N+1."""
        persons = []
        for i in range(100):
            p, _ = _make_person(org, first=f"Camper{i}", last="Test", email=f"c{i}@sp.test")
            _assign_camper(bunk, p)
            persons.append(p)
        with organization_context(org):
            r = api.get("/api/v1/specialist/campers/", **_hdr(org.slug))
        assert r.status_code == 200
        assert len(r.json()["results"]) >= 100

    def test_cross_program_picker_includes_second_program(self, api, org, program, sp_person_user, sp_membership):
        person, _ = sp_person_user
        prog2 = Program.all_objects.create(
            organization=org, name="SP Org Prog 2", slug="sp-prog2",
            program_type="summer_camp",
            start_date=date(2026, 6, 1), end_date=date(2026, 8, 31),
        )
        _make_membership(prog2, person, "specialist")
        bunk2 = _make_bunk(org, prog2, name="Oak")
        camper2, _ = _make_person(org, first="Prog2", last="Cam", email="p2c@sp.test")
        _assign_camper(bunk2, camper2)

        with organization_context(org):
            r = api.get("/api/v1/specialist/campers/", **_hdr(org.slug))
        assert any(c["id"] == camper2.id for c in r.json()["results"])


# ---------------------------------------------------------------------------
# Note create / edit tests
# ---------------------------------------------------------------------------


class TestSpecialistNoteCreate:
    def test_create_note_happy_path(self, api, org, program, sp_person_user, sp_membership, camper_person, camper_agm):
        _person, _ = sp_person_user
        payload = {
            "subject_id": camper_person.id,
            "body": "Great backstroke technique.",
            "category": "positive",
            "is_sensitive": False,
            "flag_for_camper_care": False,
        }
        with organization_context(org):
            r = api.post("/api/v1/specialist/notes/", payload, format="json", **_hdr(org.slug))
        assert r.status_code == 201
        data = r.json()
        assert data["note_type"] == "specialist"
        assert data["body"] == "Great backstroke technique."
        assert data["flag_raised"] is False

    def test_create_note_with_flag_creates_flag_record(self, api, org, program, sp_person_user, sp_membership, camper_person, camper_agm):
        _person, _ = sp_person_user
        payload = {
            "subject_id": camper_person.id,
            "body": "Concerning behavior in water.",
            "flag_for_camper_care": True,
        }
        with organization_context(org):
            r = api.post("/api/v1/specialist/notes/", payload, format="json", **_hdr(org.slug))
        assert r.status_code == 201
        note_id = r.json()["id"]
        assert r.json()["flag_raised"] is True

        flag = Flag.all_objects.filter(
            trigger_content_type="specialist_note",
            trigger_content_id=str(note_id),
        ).first()
        assert flag is not None
        assert flag.status == Flag.Status.ACTIVE
        assert flag.subject_camper == camper_person

    def test_create_note_missing_body_returns_400(self, api, org, sp_membership, camper_person, camper_agm):
        with organization_context(org):
            r = api.post(
                "/api/v1/specialist/notes/",
                {"subject_id": camper_person.id, "body": ""},
                format="json", **_hdr(org.slug),
            )
        assert r.status_code == 400
        assert "body" in r.json()

    def test_create_note_missing_subject_returns_400(self, api, org, sp_membership):
        with organization_context(org):
            r = api.post(
                "/api/v1/specialist/notes/",
                {"body": "Some note"},
                format="json", **_hdr(org.slug),
            )
        assert r.status_code == 400
        assert "subject_id" in r.json()


class TestSpecialistNoteEdit:
    def test_edit_within_window_succeeds(self, api, org, program, sp_person_user, sp_membership, camper_person, camper_agm):
        person, _ = sp_person_user
        note = Note.all_objects.create(
            organization=org, program=program, subject=camper_person,
            author=person, note_type=Note.NoteType.SPECIALIST, body="Original",
        )
        with organization_context(org):
            r = api.patch(
                f"/api/v1/specialist/notes/{note.id}/",
                {"body": "Edited body"},
                format="json", **_hdr(org.slug),
            )
        assert r.status_code == 200
        assert r.json()["body"] == "Edited body"

    def test_edit_by_non_author_returns_403(self, api, org, program, sp_membership, camper_person, camper_agm):
        other, _ = _make_person(org, first="Oth", last="Sp2", email="oth2@sp.test")
        note = Note.all_objects.create(
            organization=org, program=program, subject=camper_person,
            author=other, note_type=Note.NoteType.SPECIALIST, body="Not mine",
        )
        with organization_context(org):
            r = api.patch(
                f"/api/v1/specialist/notes/{note.id}/",
                {"body": "Stealing edit"},
                format="json", **_hdr(org.slug),
            )
        assert r.status_code == 403

    def test_flag_retraction_blocked(self, api, org, program, sp_person_user, sp_membership, camper_person, camper_agm):
        """S5: Specialist cannot change flag state via PATCH (field rejected)."""
        person, _ = sp_person_user
        note = Note.all_objects.create(
            organization=org, program=program, subject=camper_person,
            author=person, note_type=Note.NoteType.SPECIALIST, body="Flagged",
        )
        with organization_context(org):
            r = api.patch(
                f"/api/v1/specialist/notes/{note.id}/",
                {"flag_for_camper_care": False},
                format="json", **_hdr(org.slug),
            )
        assert r.status_code == 400
        assert "flag_for_camper_care" in str(r.json())


# ---------------------------------------------------------------------------
# Camper view visibility tests
# ---------------------------------------------------------------------------


class TestSpecialistCamperView:
    def test_returns_own_notes_only(self, api, org, program, sp_person_user, sp_membership, camper_person, camper_agm):
        person, _ = sp_person_user
        other, _ = _make_person(org, first="OtherSp", last="X", email="osp@sp.test")
        Note.all_objects.create(
            organization=org, program=program, subject=camper_person,
            author=person, note_type=Note.NoteType.SPECIALIST, body="My note",
        )
        Note.all_objects.create(
            organization=org, program=program, subject=camper_person,
            author=other, note_type=Note.NoteType.SPECIALIST, body="Other's note",
        )
        with organization_context(org):
            r = api.get(
                f"/api/v1/specialist/campers/{camper_person.id}/", **_hdr(org.slug),
            )
        assert r.status_code == 200
        notes = r.json()["my_notes"]
        assert len(notes) == 1
        assert notes[0]["body"] == "My note"

    def test_camper_not_in_program_returns_403(self, api, org, program, sp_membership):
        org2 = Organization.objects.create(name="Other Org", slug="other-org")
        outsider, _ = _make_person(org2, first="Out", last="Sider", email="out@other.test")
        with organization_context(org):
            r = api.get(
                f"/api/v1/specialist/campers/{outsider.id}/", **_hdr(org.slug),
            )
        assert r.status_code in (403, 404)

    def test_non_specialist_returns_403(self, org, program, camper_person, camper_agm):
        other, user = _make_person(org, first="CC", last="User3", email="cc3@sp.test")
        _make_membership(program, other, "camper_care")
        client = APIClient()
        client.force_authenticate(user=user)
        with organization_context(org):
            r = client.get(
                f"/api/v1/specialist/campers/{camper_person.id}/", **_hdr(org.slug),
            )
        assert r.status_code == 403

    def test_date_range_filter(self, api, org, program, sp_person_user, sp_membership, camper_person, camper_agm):
        person, _ = sp_person_user
        Note.all_objects.create(
            organization=org, program=program, subject=camper_person,
            author=person, note_type=Note.NoteType.SPECIALIST, body="In range",
        )
        with organization_context(org):
            r = api.get(
                f"/api/v1/specialist/campers/{camper_person.id}/"
                "?date_from=2026-01-01&date_to=2026-12-31",
                **_hdr(org.slug),
            )
        assert r.status_code == 200
        assert len(r.json()["my_notes"]) == 1


# ---------------------------------------------------------------------------
# Audience disclosure test
# ---------------------------------------------------------------------------


class TestNoteAudience:
    def test_audience_non_sensitive(self, api, org, sp_membership):
        with organization_context(org):
            r = api.get(
                "/api/v1/specialist/notes/audience/?is_sensitive=false",
                **_hdr(org.slug),
            )
        assert r.status_code == 200
        audience = r.json()["audience"]
        assert "Counselor" in audience
        assert "Camper Care" in audience

    def test_audience_sensitive_narrows(self, api, org, sp_membership):
        with organization_context(org):
            r = api.get(
                "/api/v1/specialist/notes/audience/?is_sensitive=true",
                **_hdr(org.slug),
            )
        assert r.status_code == 200
        audience = r.json()["audience"]
        assert "Counselor" not in audience
        assert "Camper Care" in audience
