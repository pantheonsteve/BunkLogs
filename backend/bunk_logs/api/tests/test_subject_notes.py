"""Tests for the SubjectNote API (Prompt 3.15).

Covers: happy-path create/list, visibility gating, amendment chain,
404/403 guards, and inclusion in the subject dashboard payload.
"""

from __future__ import annotations

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from bunk_logs.core.models import (
    AssignmentGroup,
    AssignmentGroupMembership,
    Membership,
    Organization,
    Person,
    Program,
    SubjectNote,
)

User = get_user_model()
pytestmark = pytest.mark.django_db


def _hdr(slug: str) -> dict:
    return {"HTTP_X_ORGANIZATION_SLUG": slug}


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Notes Org", slug="notes-org")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org, name="Notes Org Summer 2026", slug="notes-prog",
        program_type="summer_camp",
        start_date=date(2026, 6, 1), end_date=date(2026, 8, 31),
    )


def _person(org, first, last, user=None):
    return Person.all_objects.create(
        organization=org, first_name=first, last_name=last, user=user,
    )


def _user(email):
    return User.objects.create_user(email=email, password="pw")


@pytest.fixture
def setup(org, program):
    """Bunk + camper + counselor (author of bunk) + unit_head (supervisor above bunk)."""
    bunk = AssignmentGroup.all_objects.create(
        organization=org, program=program, name="Bunk Test",
        slug="notes-bunk", group_type="bunk",
    )
    camper = _person(org, "Kim", "Camper")
    AssignmentGroupMembership.all_objects.create(
        group=bunk, person=camper, role_in_group="subject", is_active=True,
    )
    Membership.all_objects.create(program=program, person=camper, role="camper", is_active=True)

    cns_user = _user("cns-notes@a.com")
    counselor = _person(org, "Coun", "Selor", cns_user)
    Membership.all_objects.create(program=program, person=counselor, role="counselor", is_active=True)
    AssignmentGroupMembership.all_objects.create(
        group=bunk, person=counselor, role_in_group="author", is_active=True,
    )

    lt_user = _user("lt-notes@a.com")
    lt = _person(org, "Lead", "Er", lt_user)
    Membership.all_objects.create(program=program, person=lt, role="leadership_team", is_active=True)

    hc_user = _user("hc-notes@a.com")
    hc = _person(org, "Health", "Center", hc_user)
    Membership.all_objects.create(program=program, person=hc, role="health_center", is_active=True)

    return bunk, camper, cns_user, counselor, lt_user, lt, hc_user, hc


# ---------------------------------------------------------------------------
# Happy-path create and list
# ---------------------------------------------------------------------------

def test_program_lead_can_create_note(api_client, org, setup):
    _, camper, _, _, lt_user, _, _, _ = setup
    api_client.force_authenticate(user=lt_user)
    r = api_client.post(
        f"/api/v1/subjects/{camper.id}/notes/",
        {"body": "LT note", "visibility": "supervisors_only"},
        **_hdr(org.slug),
    )
    assert r.status_code == 201, r.content
    data = r.json()
    assert data["body"] == "LT note"
    assert data["visibility"] == "supervisors_only"
    assert SubjectNote.all_objects.filter(subject=camper).count() == 1


def test_counselor_can_create_note_for_their_camper(api_client, org, setup):
    _, camper, cns_user, _, _, _, _, _ = setup
    api_client.force_authenticate(user=cns_user)
    r = api_client.post(
        f"/api/v1/subjects/{camper.id}/notes/",
        {"body": "Counselor note", "visibility": "team"},
        **_hdr(org.slug),
    )
    assert r.status_code == 201, r.content


def test_list_returns_visible_notes(api_client, org, program, setup):
    _, camper, cns_user, counselor, lt_user, lt, hc_user, _ = setup
    SubjectNote.all_objects.create(
        organization=org, program=program, subject=camper,
        author_person=lt, body="Team note", visibility="team",
    )
    SubjectNote.all_objects.create(
        organization=org, program=program, subject=camper,
        author_person=lt, body="Supervisors note", visibility="supervisors_only",
    )
    SubjectNote.all_objects.create(
        organization=org, program=program, subject=camper,
        author_person=lt, body="Domain note", visibility="domain_only",
    )
    # Counselor (participant with group access) sees team + supervisors_only
    api_client.force_authenticate(user=cns_user)
    r = api_client.get(f"/api/v1/subjects/{camper.id}/notes/", **_hdr(org.slug))
    assert r.status_code == 200
    bodies = {n["body"] for n in r.json()["notes"]}
    assert "Team note" in bodies
    assert "Supervisors note" in bodies
    assert "Domain note" not in bodies

    # Health center (domain_specialist) sees all three
    api_client.force_authenticate(user=hc_user)
    r = api_client.get(f"/api/v1/subjects/{camper.id}/notes/", **_hdr(org.slug))
    bodies = {n["body"] for n in r.json()["notes"]}
    assert bodies == {"Team note", "Supervisors note", "Domain note"}


def test_subject_visible_note_visible_to_self(api_client, org, program, setup):
    _, camper, _, _, lt_user, lt, _, _ = setup
    camper_user = _user("camper-self@a.com")
    camper.user = camper_user
    camper.save()
    SubjectNote.all_objects.create(
        organization=org, program=program, subject=camper,
        author_person=lt, body="Shared with camper",
        visibility="supervisors_only", subject_visible=True,
    )
    SubjectNote.all_objects.create(
        organization=org, program=program, subject=camper,
        author_person=lt, body="Private supervisor note",
        visibility="supervisors_only", subject_visible=False,
    )
    api_client.force_authenticate(user=camper_user)
    r = api_client.get(f"/api/v1/subjects/{camper.id}/notes/", **_hdr(org.slug))
    assert r.status_code == 200
    bodies = {n["body"] for n in r.json()["notes"]}
    assert "Shared with camper" in bodies
    assert "Private supervisor note" not in bodies


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------

def test_outsider_cannot_create_note(api_client, org, program, setup):
    _, camper, _, _, _, _, _, _ = setup
    other_user = _user("other-notes@a.com")
    other = _person(org, "Out", "Sider", other_user)
    Membership.all_objects.create(program=program, person=other, role="counselor", is_active=True)
    # No group relationship to camper
    api_client.force_authenticate(user=other_user)
    r = api_client.post(
        f"/api/v1/subjects/{camper.id}/notes/",
        {"body": "Sneaky note", "visibility": "team"},
        **_hdr(org.slug),
    )
    assert r.status_code == 403


def test_unauthenticated_blocked(api_client, org, setup):
    _, camper, _, _, _, _, _, _ = setup
    r = api_client.get(f"/api/v1/subjects/{camper.id}/notes/", **_hdr(org.slug))
    assert r.status_code == 401


def test_invalid_visibility_rejected(api_client, org, setup):
    _, camper, _, _, lt_user, _, _, _ = setup
    api_client.force_authenticate(user=lt_user)
    r = api_client.post(
        f"/api/v1/subjects/{camper.id}/notes/",
        {"body": "Note", "visibility": "bogus"},
        **_hdr(org.slug),
    )
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Amendment chain
# ---------------------------------------------------------------------------

def test_author_can_amend_own_note(api_client, org, program, setup):
    _, camper, _, _, lt_user, lt, _, _ = setup
    original = SubjectNote.all_objects.create(
        organization=org, program=program, subject=camper,
        author_person=lt, body="Original text", visibility="supervisors_only",
    )
    api_client.force_authenticate(user=lt_user)
    r = api_client.post(
        f"/api/v1/subjects/{camper.id}/notes/{original.id}/amend/",
        {"body": "Correction: additional context"},
        **_hdr(org.slug),
    )
    assert r.status_code == 201, r.content
    data = r.json()
    assert data["amendment_of"] == original.id
    assert data["body"] == "Correction: additional context"
    # Original is untouched
    original.refresh_from_db()
    assert original.body == "Original text"


def test_non_author_cannot_amend(api_client, org, program, setup):
    _, camper, cns_user, counselor, _, lt, _, _ = setup
    original = SubjectNote.all_objects.create(
        organization=org, program=program, subject=camper,
        author_person=lt, body="LT note", visibility="supervisors_only",
    )
    api_client.force_authenticate(user=cns_user)
    r = api_client.post(
        f"/api/v1/subjects/{camper.id}/notes/{original.id}/amend/",
        {"body": "Hijack"},
        **_hdr(org.slug),
    )
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Dashboard integration
# ---------------------------------------------------------------------------

def test_subject_dashboard_includes_notes(api_client, org, program, setup):
    _, camper, _, _, lt_user, lt, _, _ = setup
    SubjectNote.all_objects.create(
        organization=org, program=program, subject=camper,
        author_person=lt, body="Dashboard note", visibility="supervisors_only",
    )
    api_client.force_authenticate(user=lt_user)
    r = api_client.get(f"/api/v1/dashboards/subject/{camper.id}/", **_hdr(org.slug))
    assert r.status_code == 200
    body = r.json()
    assert "notes" in body
    assert any(n["body"] == "Dashboard note" for n in body["notes"])
