"""Tests for /api/v1/dashboards/subject/{person_id}/."""
from __future__ import annotations

from datetime import date
from datetime import timedelta

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
    return Organization.objects.create(name="Sd Org", slug="sd-org")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org, name="Sd Org Summer", slug="sd-prog",
        program_type="summer_camp",
        start_date=date(2026, 6, 1), end_date=date(2026, 8, 31),
    )


def _person(org, first, last, user=None):
    return Person.all_objects.create(
        organization=org, first_name=first, last_name=last, user=user,
    )


def _user(email):
    return User.objects.create_user(email=email, password="pw")


def _bunk_pulse_template(org):
    return ReflectionTemplate.all_objects.create(
        organization=org, name="Bunk Pulse", slug="sd-bunk-pulse",
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


def _wellness_template(org):
    return ReflectionTemplate.all_objects.create(
        organization=org, name="Wellness", slug="sd-wellness",
        cadence="weekly", role="health_center",
        subject_mode="single_subject", assignment_scope="per_subject_in_group",
        assignment_group_types=["bunk"],
        schema={
            "fields": [
                {
                    "key": "concerns",
                    "type": "textarea",
                    "dashboard_role": "open_concern",
                    "prompts": {"en": "Concerns?"},
                },
            ],
        },
    )


def _make_reflection(
    org, program, template, *, subject, author, group=None, day, answers,
):
    return Reflection.all_objects.create(
        organization=org, program=program, template=template,
        subject=subject, author=author, assignment_group=group,
        period_start=day, period_end=day,
        answers=answers, language="en", is_complete=True,
    )


@pytest.fixture
def setup(org, program):
    bunk = AssignmentGroup.all_objects.create(
        organization=org, program=program, name="Bunk Maple",
        slug="sd-bunk-maple", group_type="bunk",
    )
    camper = _person(org, "Sarah", "Levin")
    AssignmentGroupMembership.all_objects.create(
        group=bunk, person=camper, role_in_group="subject", is_active=True,
    )
    counselor_user = _user("cns-sd@a.com")
    counselor = _person(org, "Coun", "Selor", counselor_user)
    Membership.all_objects.create(
        program=program, person=counselor, role="counselor", is_active=True,
    )
    AssignmentGroupMembership.all_objects.create(
        group=bunk, person=counselor, role_in_group="author", is_active=True,
    )
    return bunk, camper, counselor_user, counselor


def test_unauthenticated_blocked(api_client, org, setup):
    _, camper, _, _ = setup
    r = api_client.get(f"/api/v1/dashboards/subject/{camper.id}/", **_hdr(org.slug))
    assert r.status_code == 401


def test_supervisor_sees_cross_template_aggregation(api_client, org, program, setup):
    _, camper, counselor_user, counselor = setup
    pulse = _bunk_pulse_template(org)
    wellness = _wellness_template(org)
    today = date.today()
    _make_reflection(
        org, program, pulse, subject=camper, author=counselor,
        day=today, answers={"overall": 4, "concerns": "missed mom"},
    )
    _make_reflection(
        org, program, pulse, subject=camper, author=counselor,
        day=today - timedelta(days=1), answers={"overall": 5, "concerns": ""},
    )
    api_client.force_authenticate(user=counselor_user)
    r = api_client.get(
        f"/api/v1/dashboards/subject/{camper.id}/", **_hdr(org.slug),
    )
    assert r.status_code == 200, r.content
    body = r.json()
    assert body["subject"]["name"] == "Sarah Levin"
    assert len(body["templates"]) == 1
    series = body["templates"][0]["rating_series"]
    assert any(s["label"] == "overall" for s in series)
    overall_points = next(s for s in series if s["label"] == "overall")["points"]
    assert {(p["date"], p["value"]) for p in overall_points} == {
        (today.isoformat(), 4.0),
        ((today - timedelta(days=1)).isoformat(), 5.0),
    }
    # Recent text response surfaced
    texts = body["recent_texts"]
    assert any(t["text"] == "missed mom" for t in texts)


def test_low_rating_surfaces_concerning_pattern(api_client, org, program, setup):
    _, camper, counselor_user, counselor = setup
    pulse = _bunk_pulse_template(org)
    today = date.today()
    _make_reflection(
        org, program, pulse, subject=camper, author=counselor,
        day=today, answers={"overall": 1},
    )
    api_client.force_authenticate(user=counselor_user)
    r = api_client.get(
        f"/api/v1/dashboards/subject/{camper.id}/", **_hdr(org.slug),
    )
    body = r.json()
    kinds = {p["kind"] for p in body["concerning_patterns"]}
    assert "low_rating" in kinds


def test_downward_trend_surfaces(api_client, org, program, setup):
    _, camper, counselor_user, counselor = setup
    pulse = _bunk_pulse_template(org)
    today = date.today()
    # Prior half (days 13-7 ago): mean ~ 4.5
    for i in range(7, 14):
        _make_reflection(
            org, program, pulse, subject=camper, author=counselor,
            day=today - timedelta(days=i), answers={"overall": 5},
        )
    # Recent half (days 0-6 ago): mean ~ 2.5  (drop > 0.5)
    for i in range(0, 7):
        _make_reflection(
            org, program, pulse, subject=camper, author=counselor,
            day=today - timedelta(days=i), answers={"overall": 2},
        )
    api_client.force_authenticate(user=counselor_user)
    r = api_client.get(
        f"/api/v1/dashboards/subject/{camper.id}/", **_hdr(org.slug),
    )
    body = r.json()
    kinds = {p["kind"] for p in body["concerning_patterns"]}
    assert "downward_trend" in kinds


def test_flat_series_does_not_false_positive(api_client, org, program, setup):
    _, camper, counselor_user, counselor = setup
    pulse = _bunk_pulse_template(org)
    today = date.today()
    # Stable rating of 3 across the window — small ±0.0 variance shouldn't trigger
    for i in range(0, 14):
        _make_reflection(
            org, program, pulse, subject=camper, author=counselor,
            day=today - timedelta(days=i), answers={"overall": 3},
        )
    api_client.force_authenticate(user=counselor_user)
    r = api_client.get(
        f"/api/v1/dashboards/subject/{camper.id}/", **_hdr(org.slug),
    )
    body = r.json()
    kinds = {p["kind"] for p in body["concerning_patterns"]}
    assert "downward_trend" not in kinds


def test_subject_visible_false_blocks_camper_self_view(api_client, org, program, setup):
    """A camper with no special viewing privileges sees nothing about themselves
    when the bunk_pulse template's subject_visible defaults to False."""
    _, camper, _, counselor = setup
    pulse = _bunk_pulse_template(org)
    today = date.today()
    _make_reflection(
        org, program, pulse, subject=camper, author=counselor,
        day=today, answers={"overall": 4},
    )
    camper_user = _user("camper-sd@a.com")
    camper.user = camper_user
    camper.save()
    Membership.all_objects.create(
        program=program, person=camper, role="camper", is_active=True,
    )
    api_client.force_authenticate(user=camper_user)
    r = api_client.get(
        f"/api/v1/dashboards/subject/{camper.id}/", **_hdr(org.slug),
    )
    body = r.json()
    assert body["templates"] == []  # no visibility


def test_subject_visible_true_allows_camper_self_view(api_client, org, program, setup):
    _, camper, _, counselor = setup
    visible_tpl = ReflectionTemplate.all_objects.create(
        organization=org, name="Self-Visible", slug="sd-visible",
        cadence="daily",
        subject_mode="single_subject", assignment_scope="per_subject_in_group",
        assignment_group_types=["bunk"], subject_visible=True,
        schema={"fields": [
            {"key": "overall", "type": "single_rating",
             "dashboard_role": "primary_rating",
             "scale": [1, 5], "scale_labels": {"en": ["1", "2", "3", "4", "5"]},
             "required": True},
        ]},
    )
    today = date.today()
    _make_reflection(
        org, program, visible_tpl, subject=camper, author=counselor,
        day=today, answers={"overall": 4},
    )
    camper_user = _user("camper-sd2@a.com")
    camper.user = camper_user
    camper.save()
    Membership.all_objects.create(
        program=program, person=camper, role="camper", is_active=True,
    )
    api_client.force_authenticate(user=camper_user)
    r = api_client.get(
        f"/api/v1/dashboards/subject/{camper.id}/", **_hdr(org.slug),
    )
    body = r.json()
    assert any(t["template"]["id"] == visible_tpl.id for t in body["templates"])
