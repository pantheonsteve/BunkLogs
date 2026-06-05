"""Tests for /api/v1/dashboards/concerns/."""
from __future__ import annotations

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import ConcernReadState
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import Supervision

User = get_user_model()
pytestmark = pytest.mark.django_db


def _hdr(slug: str) -> dict:
    return {"HTTP_X_ORGANIZATION_SLUG": slug}


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Cn Org", slug="cn-org")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org, name="Cn Org Summer", slug="cn-prog",
        program_type="summer_camp",
        start_date=date(2026, 6, 1), end_date=date(2026, 8, 31),
    )


def _person(org, first, last, user=None):
    return Person.all_objects.create(
        organization=org, first_name=first, last_name=last, user=user,
    )


def _user(email):
    return User.objects.create_user(email=email, password="pw")


def _bunk_obs(org):
    return ReflectionTemplate.all_objects.create(
        organization=org, name="Bunk Obs", slug="cn-bunk-obs",
        cadence="daily",
        subject_mode="single_subject", assignment_scope="per_subject_in_group",
        assignment_group_types=["bunk"],
        author_role_filter=["counselor"], subject_role_filter=["camper"],
        schema={
            "fields": [
                {
                    "key": "overall",
                    "type": "single_rating",
                    "dashboard_role": "primary_rating",
                    "scale": [1, 5],
                    "scale_labels": {"en": ["1", "2", "3", "4", "5"]},
                    "required": True,
                },
                {
                    "key": "concerns",
                    "type": "textarea",
                    "dashboard_role": "open_concern",
                    "prompts": {"en": "Concerns?"},
                    "required": False,
                },
            ],
        },
    )


@pytest.fixture
def setup(org, program):
    bunk = AssignmentGroup.all_objects.create(
        organization=org, program=program, name="B",
        slug="cn-b", group_type="bunk",
    )
    camper = _person(org, "Cam", "Per")
    AssignmentGroupMembership.all_objects.create(
        group=bunk, person=camper, role_in_group="subject", is_active=True,
    )
    counselor_user = _user("cns-cn@a.com")
    counselor = _person(org, "Co", "Un", counselor_user)
    Membership.all_objects.create(
        program=program, person=counselor, role="counselor", is_active=True,
    )
    AssignmentGroupMembership.all_objects.create(
        group=bunk, person=counselor, role_in_group="author", is_active=True,
    )
    return bunk, camper, counselor_user, counselor


def _make_reflection(
    org, program, template, *, subject, author, group, day, answers,
    team_visibility=Reflection.TeamVisibility.TEAM,
):
    return Reflection.all_objects.create(
        organization=org, program=program, template=template,
        subject=subject, author=author, assignment_group=group,
        period_start=day, period_end=day,
        answers=answers, language="en", is_complete=True,
        team_visibility=team_visibility,
    )


# ── Listing ──────────────────────────────────────────────────────────────────


def test_concern_items_expose_team_visibility(api_client, org, program, setup):
    """3.24: ConcernsInbox renders the PrivacyChip beside the KindBadge."""
    bunk, camper, counselor_user, counselor = setup
    tpl = _bunk_obs(org)
    today = date.today()
    _make_reflection(
        org, program, tpl, subject=camper, author=counselor, group=bunk,
        day=today, answers={"overall": 4, "concerns": "private worry"},
        team_visibility=Reflection.TeamVisibility.SUPERVISORS_ONLY,
    )
    api_client.force_authenticate(user=counselor_user)
    r = api_client.get("/api/v1/dashboards/concerns/", **_hdr(org.slug))
    body = r.json()
    private = next(i for i in body["items"] if i["value"] == "private worry")
    assert private["team_visibility"] == "supervisors_only"


def test_open_concern_text_appears(api_client, org, program, setup):
    bunk, camper, counselor_user, counselor = setup
    tpl = _bunk_obs(org)
    today = date.today()
    _make_reflection(
        org, program, tpl, subject=camper, author=counselor, group=bunk,
        day=today, answers={"overall": 4, "concerns": "missed family"},
    )
    api_client.force_authenticate(user=counselor_user)
    r = api_client.get("/api/v1/dashboards/concerns/", **_hdr(org.slug))
    body = r.json()
    assert any(
        i["kind"] == "open_concern" and i["value"] == "missed family"
        for i in body["items"]
    )


def test_low_rating_appears(api_client, org, program, setup):
    bunk, camper, counselor_user, counselor = setup
    tpl = _bunk_obs(org)
    today = date.today()
    _make_reflection(
        org, program, tpl, subject=camper, author=counselor, group=bunk,
        day=today, answers={"overall": 1},
    )
    api_client.force_authenticate(user=counselor_user)
    r = api_client.get("/api/v1/dashboards/concerns/", **_hdr(org.slug))
    body = r.json()
    assert any(
        i["kind"] == "low_rating" and i["value"] == 1.0
        for i in body["items"]
    )


def test_empty_concern_text_skipped(api_client, org, program, setup):
    bunk, camper, counselor_user, counselor = setup
    tpl = _bunk_obs(org)
    today = date.today()
    _make_reflection(
        org, program, tpl, subject=camper, author=counselor, group=bunk,
        day=today, answers={"overall": 4, "concerns": "   "},
    )
    api_client.force_authenticate(user=counselor_user)
    r = api_client.get("/api/v1/dashboards/concerns/", **_hdr(org.slug))
    body = r.json()
    assert not any(i["kind"] == "open_concern" for i in body["items"])


# ── Read state ────────────────────────────────────────────────────────────────


def test_mark_read_hides_item_from_default_view(api_client, org, program, setup):
    bunk, camper, counselor_user, counselor = setup
    tpl = _bunk_obs(org)
    today = date.today()
    ref = _make_reflection(
        org, program, tpl, subject=camper, author=counselor, group=bunk,
        day=today, answers={"overall": 4, "concerns": "tough day"},
    )
    api_client.force_authenticate(user=counselor_user)
    # Mark it read
    r = api_client.post(
        f"/api/v1/dashboards/concerns/{ref.id}/concerns/read/",
        **_hdr(org.slug),
    )
    assert r.status_code == 200
    # Default fetch hides it
    r = api_client.get("/api/v1/dashboards/concerns/", **_hdr(org.slug))
    body = r.json()
    assert not any(i["reflection_id"] == ref.id for i in body["items"])
    # include_read=true brings it back, marked as read
    r = api_client.get(
        "/api/v1/dashboards/concerns/?include_read=true",
        **_hdr(org.slug),
    )
    body = r.json()
    item = next(i for i in body["items"] if i["reflection_id"] == ref.id)
    assert item["read"] is True


def test_mark_read_blocked_for_invisible_reflection(
    api_client, org, program, setup,
):
    bunk, camper, _, counselor = setup
    tpl = _bunk_obs(org)
    today = date.today()
    ref = _make_reflection(
        org, program, tpl, subject=camper, author=counselor, group=bunk,
        day=today, answers={"overall": 1},
    )
    other_user = _user("nobody@a.com")
    other = _person(org, "No", "Body", other_user)
    Membership.all_objects.create(
        program=program, person=other, role="counselor", is_active=True,
    )
    api_client.force_authenticate(user=other_user)
    r = api_client.post(
        f"/api/v1/dashboards/concerns/{ref.id}/overall/read/",
        **_hdr(org.slug),
    )
    assert r.status_code == 404
    assert ConcernReadState.objects.count() == 0


def test_unmark_read_restores_item(api_client, org, program, setup):
    bunk, camper, counselor_user, counselor = setup
    tpl = _bunk_obs(org)
    today = date.today()
    ref = _make_reflection(
        org, program, tpl, subject=camper, author=counselor, group=bunk,
        day=today, answers={"overall": 4, "concerns": "tough day"},
    )
    api_client.force_authenticate(user=counselor_user)
    api_client.post(
        f"/api/v1/dashboards/concerns/{ref.id}/concerns/read/",
        **_hdr(org.slug),
    )
    r = api_client.delete(
        f"/api/v1/dashboards/concerns/{ref.id}/concerns/read/",
        **_hdr(org.slug),
    )
    assert r.status_code == 200
    body_after = api_client.get("/api/v1/dashboards/concerns/", **_hdr(org.slug)).json()
    assert any(i["reflection_id"] == ref.id for i in body_after["items"])


# ── Visibility ────────────────────────────────────────────────────────────────


def test_camper_care_concerns_limited_to_caseload_bunks(
    api_client, org, program, setup,
):
    bunk, camper, counselor_user, counselor = setup
    other_bunk = AssignmentGroup.all_objects.create(
        organization=org, program=program, name="Other",
        slug="cn-other", group_type="bunk",
    )
    other_camper = _person(org, "Ot", "Her")
    AssignmentGroupMembership.all_objects.create(
        group=other_bunk, person=other_camper, role_in_group="subject", is_active=True,
    )
    tpl = _bunk_obs(org)
    today = date.today()
    _make_reflection(
        org, program, tpl, subject=camper, author=counselor, group=bunk,
        day=today, answers={"overall": 4, "concerns": "on caseload"},
    )
    _make_reflection(
        org, program, tpl, subject=other_camper, author=counselor, group=other_bunk,
        day=today, answers={"overall": 4, "concerns": "off caseload"},
    )
    cc_user = _user("cc-cn@a.com")
    cc_person = _person(org, "Cc", "Care", cc_user)
    cc_membership = Membership.all_objects.create(
        program=program, person=cc_person, role="camper_care", is_active=True,
    )
    Supervision.all_objects.create(
        supervisor_membership=cc_membership,
        target_type="bunk",
        target_bunk=bunk,
        start_date=date(2026, 1, 1),
    )
    api_client.force_authenticate(user=cc_user)
    r = api_client.get("/api/v1/dashboards/concerns/", **_hdr(org.slug))
    body = r.json()
    values = [i["value"] for i in body["items"] if i["kind"] == "open_concern"]
    assert "on caseload" in values
    assert "off caseload" not in values


def test_invisible_concerns_not_listed(api_client, org, program, setup):
    bunk, camper, _, counselor = setup
    tpl = _bunk_obs(org)
    today = date.today()
    _make_reflection(
        org, program, tpl, subject=camper, author=counselor, group=bunk,
        day=today, answers={"overall": 1, "concerns": "secret"},
    )
    other = _user("other@a.com")
    p = _person(org, "Ot", "Her", other)
    Membership.all_objects.create(
        program=program, person=p, role="counselor", is_active=True,
    )
    api_client.force_authenticate(user=other)
    r = api_client.get("/api/v1/dashboards/concerns/", **_hdr(org.slug))
    body = r.json()
    assert body["items"] == []
