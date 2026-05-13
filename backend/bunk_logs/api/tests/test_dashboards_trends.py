"""Tests for /api/v1/dashboards/subject-trends/."""
from __future__ import annotations

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate

User = get_user_model()
pytestmark = pytest.mark.django_db


def _hdr(slug: str) -> dict:
    return {"HTTP_X_ORGANIZATION_SLUG": slug}


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Tr Org", slug="tr-org")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org, name="Tr Org Summer", slug="tr-prog",
        program_type="summer_camp",
        start_date=date(2026, 6, 1), end_date=date(2026, 8, 31),
    )


def _person(org, first, last, user=None):
    return Person.all_objects.create(
        organization=org, first_name=first, last_name=last, user=user,
    )


def _user(email: str):
    return User.objects.create_user(email=email, password="pw")


def _primary_rating_template(org, scale_max=4):
    return ReflectionTemplate.all_objects.create(
        organization=org, name="Bunk Pulse", slug="bunk-pulse",
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
                    "scale": [1, scale_max],
                    "scale_labels": {"en": [str(i) for i in range(1, scale_max + 1)]},
                    "required": True,
                },
            ],
        },
    )


def _category_rating_template(org):
    return ReflectionTemplate.all_objects.create(
        organization=org, name="Bunk Multi", slug="bunk-multi",
        cadence="daily",
        subject_mode="single_subject", assignment_scope="per_subject_in_group",
        assignment_group_types=["bunk"],
        author_role_filter=["counselor"], subject_role_filter=["camper"],
        schema={
            "fields": [
                {
                    "key": "pulse",
                    "type": "rating_group",
                    "dashboard_role": "category_ratings",
                    "scale": [1, 5],
                    "scale_labels": {"en": ["1", "2", "3", "4", "5"]},
                    "categories": [
                        {"key": "morale", "labels": {"en": "Morale"}},
                        {"key": "energy", "labels": {"en": "Energy"}},
                    ],
                    "required": True,
                },
            ],
        },
    )


def _make_reflection(org, program, template, *, subject, author, group, day, answers):
    return Reflection.all_objects.create(
        organization=org, program=program, template=template,
        subject=subject, author=author, assignment_group=group,
        period_start=day, period_end=day,
        answers=answers, language="en", is_complete=True,
    )


@pytest.fixture
def setup_bunk(org, program):
    bunk = AssignmentGroup.all_objects.create(
        organization=org, program=program, name="Bunk Maple",
        slug="bunk-maple", group_type="bunk",
    )
    campers = [_person(org, f"C{i}", f"L{i}") for i in range(3)]
    for c in campers:
        AssignmentGroupMembership.all_objects.create(
            group=bunk, person=c, role_in_group="subject", is_active=True,
        )
    counselor_user = _user("cns@a.com")
    counselor = _person(org, "Co", "Un", counselor_user)
    Membership.all_objects.create(
        program=program, person=counselor, role="counselor", is_active=True,
    )
    AssignmentGroupMembership.all_objects.create(
        group=bunk, person=counselor, role_in_group="author", is_active=True,
    )
    return bunk, campers, counselor_user, counselor


# ── Required parameters & 404 ─────────────────────────────────────────────────


def test_missing_params_returns_400(api_client, org):
    u = _user("admin@a.com")
    p = _person(org, "Ad", "Min", u)
    Membership.all_objects.create(
        program=Program.all_objects.first(),
        person=p, role="admin", is_active=True,
    ) if Program.all_objects.exists() else None
    api_client.force_authenticate(user=u)
    r = api_client.get("/api/v1/dashboards/subject-trends/", **_hdr(org.slug))
    assert r.status_code == 400


def test_unknown_group_returns_404(api_client, org, program):
    u = _user("admin@a.com")
    p = _person(org, "Ad", "Min", u)
    Membership.all_objects.create(
        program=program, person=p, role="admin", is_active=True,
    )
    tpl = _primary_rating_template(org)
    api_client.force_authenticate(user=u)
    r = api_client.get(
        f"/api/v1/dashboards/subject-trends/?assignment_group=99999&template={tpl.id}",
        **_hdr(org.slug),
    )
    assert r.status_code == 404


# ── Visibility ────────────────────────────────────────────────────────────────


def test_supervisor_can_access_own_group(api_client, org, program, setup_bunk):
    bunk, campers, counselor_user, _ = setup_bunk
    tpl = _primary_rating_template(org, scale_max=4)
    api_client.force_authenticate(user=counselor_user)
    r = api_client.get(
        f"/api/v1/dashboards/subject-trends/?assignment_group={bunk.id}&template={tpl.id}",
        **_hdr(org.slug),
    )
    assert r.status_code == 200, r.content
    body = r.json()
    assert body["group"]["id"] == bunk.id
    assert len(body["subjects"]) == len(campers)
    assert body["scale_max"] == 4


def test_other_counselor_blocked(api_client, org, program, setup_bunk):
    bunk, _, _, _ = setup_bunk
    tpl = _primary_rating_template(org)
    other = _user("other@a.com")
    p = _person(org, "Ot", "Her", other)
    Membership.all_objects.create(
        program=program, person=p, role="counselor", is_active=True,
    )
    api_client.force_authenticate(user=other)
    r = api_client.get(
        f"/api/v1/dashboards/subject-trends/?assignment_group={bunk.id}&template={tpl.id}",
        **_hdr(org.slug),
    )
    assert r.status_code == 403


# ── Primary rating mode ───────────────────────────────────────────────────────


def test_primary_rating_returns_per_cell_values(api_client, org, program, setup_bunk):
    bunk, campers, counselor_user, counselor = setup_bunk
    tpl = _primary_rating_template(org, scale_max=4)
    today = date.today()
    yesterday = date(today.year, today.month, today.day) - __import__("datetime").timedelta(days=1)
    _make_reflection(
        org, program, tpl, subject=campers[0], author=counselor, group=bunk,
        day=today, answers={"overall": 4},
    )
    _make_reflection(
        org, program, tpl, subject=campers[0], author=counselor, group=bunk,
        day=yesterday, answers={"overall": 1},
    )
    _make_reflection(
        org, program, tpl, subject=campers[1], author=counselor, group=bunk,
        day=today, answers={"overall": 3},
    )
    api_client.force_authenticate(user=counselor_user)
    r = api_client.get(
        f"/api/v1/dashboards/subject-trends/?assignment_group={bunk.id}&template={tpl.id}"
        f"&date_start={yesterday.isoformat()}&date_end={today.isoformat()}",
        **_hdr(org.slug),
    )
    assert r.status_code == 200
    body = r.json()
    by_id = {s["person_id"]: s for s in body["subjects"]}
    c0_cells = {c["date"]: c["rating"] for c in by_id[campers[0].id]["cells"]}
    assert c0_cells[today.isoformat()] == 4
    assert c0_cells[yesterday.isoformat()] == 1
    c1_cells = {c["date"]: c["rating"] for c in by_id[campers[1].id]["cells"]}
    assert c1_cells[today.isoformat()] == 3
    # Camper 2 has no reflections; cells are null
    c2_cells = {c["date"]: c["rating"] for c in by_id[campers[2].id]["cells"]}
    assert all(v is None for v in c2_cells.values())


# ── Category ratings mode ─────────────────────────────────────────────────────


def test_category_ratings_average_when_no_filter(api_client, org, program, setup_bunk):
    bunk, campers, counselor_user, counselor = setup_bunk
    tpl = _category_rating_template(org)
    today = date.today()
    _make_reflection(
        org, program, tpl, subject=campers[0], author=counselor, group=bunk,
        day=today, answers={"pulse": {"morale": 4, "energy": 2}},
    )
    api_client.force_authenticate(user=counselor_user)
    r = api_client.get(
        f"/api/v1/dashboards/subject-trends/?assignment_group={bunk.id}&template={tpl.id}"
        f"&date_start={today.isoformat()}&date_end={today.isoformat()}",
        **_hdr(org.slug),
    )
    body = r.json()
    by_id = {s["person_id"]: s for s in body["subjects"]}
    c0_today = next(c for c in by_id[campers[0].id]["cells"] if c["date"] == today.isoformat())
    assert c0_today["rating"] == 3.0
    assert body["scale_max"] == 5


def test_category_ratings_filtered_to_one_category(api_client, org, program, setup_bunk):
    bunk, campers, counselor_user, counselor = setup_bunk
    tpl = _category_rating_template(org)
    today = date.today()
    _make_reflection(
        org, program, tpl, subject=campers[0], author=counselor, group=bunk,
        day=today, answers={"pulse": {"morale": 5, "energy": 1}},
    )
    api_client.force_authenticate(user=counselor_user)
    r = api_client.get(
        f"/api/v1/dashboards/subject-trends/?assignment_group={bunk.id}&template={tpl.id}"
        f"&date_start={today.isoformat()}&date_end={today.isoformat()}&category=morale",
        **_hdr(org.slug),
    )
    body = r.json()
    by_id = {s["person_id"]: s for s in body["subjects"]}
    c0_today = next(c for c in by_id[campers[0].id]["cells"] if c["date"] == today.isoformat())
    assert c0_today["rating"] == 5.0
    assert body["category_filter"] == "morale"


def test_category_ratings_unknown_category_returns_400(api_client, org, program, setup_bunk):
    bunk, campers, counselor_user, _ = setup_bunk
    tpl = _category_rating_template(org)
    today = date.today()
    api_client.force_authenticate(user=counselor_user)
    r = api_client.get(
        f"/api/v1/dashboards/subject-trends/?assignment_group={bunk.id}&template={tpl.id}"
        f"&date_start={today.isoformat()}&date_end={today.isoformat()}&category=nope",
        **_hdr(org.slug),
    )
    assert r.status_code == 400


# ── Tooltip / aria payload ────────────────────────────────────────────────────


def test_response_includes_author_for_each_filled_cell(api_client, org, program, setup_bunk):
    bunk, campers, counselor_user, counselor = setup_bunk
    tpl = _primary_rating_template(org)
    today = date.today()
    _make_reflection(
        org, program, tpl, subject=campers[0], author=counselor, group=bunk,
        day=today, answers={"overall": 3},
    )
    api_client.force_authenticate(user=counselor_user)
    r = api_client.get(
        f"/api/v1/dashboards/subject-trends/?assignment_group={bunk.id}&template={tpl.id}"
        f"&date_start={today.isoformat()}&date_end={today.isoformat()}",
        **_hdr(org.slug),
    )
    body = r.json()
    by_id = {s["person_id"]: s for s in body["subjects"]}
    c0_today = next(c for c in by_id[campers[0].id]["cells"] if c["date"] == today.isoformat())
    assert c0_today["author_id"] == counselor.id
    assert c0_today["author_name"] == counselor.full_name
    assert c0_today["reflection_id"] is not None
