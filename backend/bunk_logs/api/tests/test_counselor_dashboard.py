"""Tests for ``GET /api/v1/counselor/dashboard/`` (Step 7_6b, Stories 2 + 9).

Covers section-state computation, off-camp exclusion, all-set derivation,
co-counselor requests inclusion, and the 30s response cache.
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
from bunk_logs.core.models import CamperDayState
from bunk_logs.core.models import MaintenanceTicket
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Order
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate

User = get_user_model()

DAILY_SIMPLE_SCHEMA = {
    "fields": [
        {"key": "note", "type": "textarea", "required": False, "prompts": {"en": "Notes"}},
    ],
}

SELF_DAILY_SCHEMA = {
    "fields": [
        {"key": "day_off", "type": "yes_no", "required": False, "prompts": {"en": "Day off?"}},
        {"key": "elaboration", "type": "textarea", "required": True, "prompts": {"en": "How was today?"}},
    ],
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def org(db):
    return Organization.objects.create(name="CD Camp", slug="cd-camp", settings={"rollover_hour": 0, "timezone": "UTC"})


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="CD Camp Summer 2026",
        slug="cd-summer-2026",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def counselor_user():
    return User.objects.create_user(email="counselor@cd.test", password="pw")


@pytest.fixture
def counselor_person(org, counselor_user):
    return Person.all_objects.create(
        organization=org,
        first_name="Mira",
        last_name="Sandberg",
        user=counselor_user,
    )


@pytest.fixture
def counselor_membership(program, counselor_person):
    return Membership.all_objects.create(
        program=program, person=counselor_person, role="counselor", is_active=True,
    )


@pytest.fixture
def co_counselor_user():
    return User.objects.create_user(email="co@cd.test", password="pw")


@pytest.fixture
def co_counselor_person(org, co_counselor_user):
    return Person.all_objects.create(
        organization=org,
        first_name="Jordan",
        last_name="Patel",
        user=co_counselor_user,
    )


@pytest.fixture
def co_counselor_membership(program, co_counselor_person):
    return Membership.all_objects.create(
        program=program, person=co_counselor_person, role="counselor", is_active=True,
    )


@pytest.fixture
def bunk(org, program):
    return AssignmentGroup.objects.create(
        organization=org,
        program=program,
        name="Bunk Birch",
        slug="bunk-birch",
        group_type="bunk",
        is_active=True,
    )


@pytest.fixture
def counselor_as_author(bunk, counselor_person):
    return AssignmentGroupMembership.objects.create(
        group=bunk, person=counselor_person, role_in_group="author", is_active=True,
    )


@pytest.fixture
def co_as_author(bunk, co_counselor_person):
    return AssignmentGroupMembership.objects.create(
        group=bunk, person=co_counselor_person, role_in_group="author", is_active=True,
    )


@pytest.fixture
def campers(org, bunk):
    persons = []
    for first, last in [("Sarah", "Levin"), ("Maya", "Cohen"), ("Eli", "Roth")]:
        p = Person.all_objects.create(organization=org, first_name=first, last_name=last)
        AssignmentGroupMembership.objects.create(
            group=bunk, person=p, role_in_group="subject", is_active=True,
        )
        persons.append(p)
    return persons


@pytest.fixture
def camper_template(org):
    return ReflectionTemplate.all_objects.create(
        organization=org,
        name="Bunk Log",
        slug="bunk-log-cd",
        cadence="daily",
        subject_mode="single_subject",
        assignment_group_types=["bunk"],
        schema=DAILY_SIMPLE_SCHEMA,
        languages=["en"],
        is_active=True,
        program_type="summer_camp",
        author_role_filter=["counselor"],
    )


@pytest.fixture
def self_template(org):
    return ReflectionTemplate.all_objects.create(
        organization=org,
        name="Counselor Self",
        slug="counselor-self-cd",
        cadence="daily",
        subject_mode="self",
        role="counselor",
        schema=SELF_DAILY_SCHEMA,
        languages=["en"],
        is_active=True,
        program_type="summer_camp",
    )


def _client(user, org):
    c = APIClient()
    c.force_authenticate(user=user)
    c.credentials(HTTP_X_ORGANIZATION_SLUG=org.slug)
    return c


# ---------------------------------------------------------------------------
# Auth / org gating
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_dashboard_requires_authentication():
    c = APIClient()
    resp = c.get("/api/v1/counselor/dashboard/")
    assert resp.status_code in {401, 403}


@pytest.mark.django_db
def test_dashboard_requires_organization_context(counselor_user):
    c = APIClient()
    c.force_authenticate(user=counselor_user)
    resp = c.get("/api/v1/counselor/dashboard/")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_dashboard_requires_person_profile(org):
    user = User.objects.create_user(email="ghost@cd.test", password="pw")
    c = _client(user, org)
    with organization_context(org):
        resp = c.get("/api/v1/counselor/dashboard/?nocache=1")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Camper-reflections section
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_dashboard_empty_state_no_membership(org, counselor_user, counselor_person):
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/counselor/dashboard/?nocache=1")
    assert resp.status_code == 200
    assert resp.data["program"] is None
    assert resp.data["sections"]["camper_reflections"]["total"] == 0


@pytest.mark.django_db
def test_dashboard_none_state_when_no_reflections(
    org,
    counselor_user,
    counselor_person,
    counselor_membership,
    bunk,
    counselor_as_author,
    campers,
    camper_template,
):
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/counselor/dashboard/?nocache=1")
    section = resp.data["sections"]["camper_reflections"]
    assert section["state"] == "none"
    assert section["covered"] == 0
    assert section["total"] == 3
    assert section["off_camp"] == 0


@pytest.mark.django_db
def test_dashboard_in_progress_when_some_submitted(
    org,
    program,
    counselor_user,
    counselor_person,
    counselor_membership,
    bunk,
    counselor_as_author,
    campers,
    camper_template,
):
    today = date.today()
    Reflection.all_objects.create(
        organization=org,
        program=program,
        author=counselor_person,
        subject=campers[0],
        assignment_group=bunk,
        template=camper_template,
        period_start=today,
        period_end=today,
        answers={"note": "ok"},
        is_complete=True,
        language="en",
    )
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/counselor/dashboard/?nocache=1")
    section = resp.data["sections"]["camper_reflections"]
    assert section["state"] == "in_progress"
    assert section["covered"] == 1
    assert section["total"] == 3


@pytest.mark.django_db
def test_dashboard_complete_when_all_submitted(
    org,
    program,
    counselor_user,
    counselor_person,
    counselor_membership,
    bunk,
    counselor_as_author,
    campers,
    camper_template,
):
    today = date.today()
    for camper in campers:
        Reflection.all_objects.create(
            organization=org,
            program=program,
            author=counselor_person,
            subject=camper,
            assignment_group=bunk,
            template=camper_template,
            period_start=today,
            period_end=today,
            answers={"note": "ok"},
            is_complete=True,
            language="en",
        )
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/counselor/dashboard/?nocache=1")
    section = resp.data["sections"]["camper_reflections"]
    assert section["state"] == "complete"
    assert section["covered"] == 3
    assert section["total"] == 3


@pytest.mark.django_db
def test_dashboard_off_camp_excluded_from_expected(
    org,
    program,
    counselor_user,
    counselor_person,
    counselor_membership,
    bunk,
    counselor_as_author,
    campers,
    camper_template,
):
    today = date.today()
    # Mark one camper off-camp -> expected total drops to 2.
    CamperDayState.objects.create(
        organization=org,
        program=program,
        camper=campers[-1],
        date=today,
        is_off_camp=True,
    )
    # Submit reflections for the remaining 2 -> should be "complete".
    for camper in campers[:-1]:
        Reflection.all_objects.create(
            organization=org,
            program=program,
            author=counselor_person,
            subject=camper,
            assignment_group=bunk,
            template=camper_template,
            period_start=today,
            period_end=today,
            answers={"note": "ok"},
            is_complete=True,
            language="en",
        )
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/counselor/dashboard/?nocache=1")
    section = resp.data["sections"]["camper_reflections"]
    assert section["state"] == "complete"
    assert section["total"] == 2
    assert section["off_camp"] == 1


@pytest.mark.django_db
def test_dashboard_draft_does_not_count_as_submitted(
    org,
    program,
    counselor_user,
    counselor_person,
    counselor_membership,
    bunk,
    counselor_as_author,
    campers,
    camper_template,
):
    today = date.today()
    Reflection.all_objects.create(
        organization=org,
        program=program,
        author=counselor_person,
        subject=campers[0],
        assignment_group=bunk,
        template=camper_template,
        period_start=today,
        period_end=today,
        answers={"note": "draft"},
        is_complete=False,
        language="en",
    )
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/counselor/dashboard/?nocache=1")
    section = resp.data["sections"]["camper_reflections"]
    assert section["covered"] == 0
    assert section["state"] == "none"


# ---------------------------------------------------------------------------
# Self-reflection section
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_dashboard_self_section_complete_when_submitted(
    org,
    program,
    counselor_user,
    counselor_person,
    counselor_membership,
    self_template,
):
    today = date.today()
    Reflection.all_objects.create(
        organization=org,
        program=program,
        author=counselor_person,
        subject=counselor_person,
        template=self_template,
        period_start=today,
        period_end=today,
        answers={"elaboration": "Solid day"},
        is_complete=True,
        language="en",
    )
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/counselor/dashboard/?nocache=1")
    section = resp.data["sections"]["self_reflection"]
    assert section["state"] == "complete"
    assert section["submitted"] is True
    assert section["is_day_off"] is False
    assert section["editable"] is True
    assert section["template"]["slug"] == "counselor-self-cd"


@pytest.mark.django_db
def test_dashboard_self_section_day_off_counts_as_complete(
    org,
    program,
    counselor_user,
    counselor_person,
    counselor_membership,
    self_template,
):
    today = date.today()
    Reflection.all_objects.create(
        organization=org,
        program=program,
        author=counselor_person,
        subject=counselor_person,
        template=self_template,
        period_start=today,
        period_end=today,
        answers={"day_off": True},
        is_complete=True,
        language="en",
    )
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/counselor/dashboard/?nocache=1")
    section = resp.data["sections"]["self_reflection"]
    assert section["state"] == "complete"
    assert section["is_day_off"] is True


@pytest.mark.django_db
def test_dashboard_self_section_none_when_no_template(
    org, counselor_user, counselor_person, counselor_membership,
):
    # Strip the global counselor self-reflection template seeded by
    # migration 0029 so this scenario can exercise the "no template
    # configured at all" path. Org-scoped tenants without any
    # applicable template still hit the same branch in production
    # (e.g. a religious-school program with no counselors).
    ReflectionTemplate.all_objects.filter(
        organization__isnull=True, slug="counselor-self-reflection",
    ).delete()
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/counselor/dashboard/?nocache=1")
    section = resp.data["sections"]["self_reflection"]
    assert section["state"] == "complete"
    assert section["template"] is None


# ---------------------------------------------------------------------------
# All-set + requests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_dashboard_all_set_true_when_both_sections_complete(
    org,
    program,
    counselor_user,
    counselor_person,
    counselor_membership,
    bunk,
    counselor_as_author,
    campers,
    camper_template,
    self_template,
):
    today = date.today()
    for camper in campers:
        Reflection.all_objects.create(
            organization=org,
            program=program,
            author=counselor_person,
            subject=camper,
            assignment_group=bunk,
            template=camper_template,
            period_start=today,
            period_end=today,
            answers={"note": "ok"},
            is_complete=True,
            language="en",
        )
    Reflection.all_objects.create(
        organization=org,
        program=program,
        author=counselor_person,
        subject=counselor_person,
        template=self_template,
        period_start=today,
        period_end=today,
        answers={"elaboration": "Great"},
        is_complete=True,
        language="en",
    )
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/counselor/dashboard/?nocache=1")
    assert resp.data["all_set"] is True


@pytest.mark.django_db
def test_dashboard_all_set_false_with_open_requests_only(
    org,
    program,
    counselor_user,
    counselor_person,
    counselor_membership,
    bunk,
    counselor_as_author,
    campers,
    camper_template,
    self_template,
):
    today = date.today()
    for camper in campers:
        Reflection.all_objects.create(
            organization=org,
            program=program,
            author=counselor_person,
            subject=camper,
            assignment_group=bunk,
            template=camper_template,
            period_start=today,
            period_end=today,
            answers={"note": "ok"},
            is_complete=True,
            language="en",
        )
    Reflection.all_objects.create(
        organization=org,
        program=program,
        author=counselor_person,
        subject=counselor_person,
        template=self_template,
        period_start=today,
        period_end=today,
        answers={"elaboration": "Great"},
        is_complete=True,
        language="en",
    )
    # Open order should NOT block all-set (Story 9 criterion 2).
    Order.all_objects.create(
        organization=org,
        program=program,
        subject=campers[0],
        submitted_by=counselor_membership,
        item="Toothbrush",
        status="new",
    )
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/counselor/dashboard/?nocache=1")
    assert resp.data["all_set"] is True
    assert resp.data["sections"]["requests"]["open_count"] == 1


@pytest.mark.django_db
def test_dashboard_requests_includes_co_counselor(
    org,
    program,
    counselor_user,
    counselor_person,
    counselor_membership,
    co_counselor_person,
    co_counselor_membership,
    bunk,
    counselor_as_author,
    co_as_author,
    campers,
):
    Order.all_objects.create(
        organization=org,
        program=program,
        subject=campers[0],
        submitted_by=co_counselor_membership,
        item="Bug spray",
        status="in_progress",
    )
    MaintenanceTicket.all_objects.create(
        organization=org,
        program=program,
        submitted_by=co_counselor_membership,
        location="Bunk Birch",
        category=MaintenanceTicket.Category.LEAK,
        description="Faucet drip",
        urgency="normal",
    )
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/counselor/dashboard/?nocache=1")
    section = resp.data["sections"]["requests"]
    assert section["open_count"] == 2
    assert section["by_type"] == {"camper_care": 1, "maintenance": 1}


@pytest.mark.django_db
def test_dashboard_excludes_closed_requests_from_count(
    org,
    program,
    counselor_user,
    counselor_person,
    counselor_membership,
    bunk,
    counselor_as_author,
    campers,
):
    Order.all_objects.create(
        organization=org,
        program=program,
        subject=campers[0],
        submitted_by=counselor_membership,
        item="Toothbrush",
        status="fulfilled",
    )
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/counselor/dashboard/?nocache=1")
    section = resp.data["sections"]["requests"]
    assert section["open_count"] == 0


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_dashboard_caches_response(
    org,
    program,
    counselor_user,
    counselor_person,
    counselor_membership,
    bunk,
    counselor_as_author,
    campers,
    camper_template,
):
    c = _client(counselor_user, org)
    with organization_context(org):
        first = c.get("/api/v1/counselor/dashboard/")
    assert first.status_code == 200
    assert first.data["sections"]["camper_reflections"]["covered"] == 0

    # Add a submission AFTER the first response was cached -> cached value wins.
    today = date.today()
    Reflection.all_objects.create(
        organization=org,
        program=program,
        author=counselor_person,
        subject=campers[0],
        assignment_group=bunk,
        template=camper_template,
        period_start=today,
        period_end=today,
        answers={"note": "ok"},
        is_complete=True,
        language="en",
    )
    with organization_context(org):
        cached = c.get("/api/v1/counselor/dashboard/")
    assert cached.data == first.data

    # ?nocache=1 forces a fresh computation.
    with organization_context(org):
        fresh = c.get("/api/v1/counselor/dashboard/?nocache=1")
    assert fresh.data["sections"]["camper_reflections"]["covered"] == 1


# ---------------------------------------------------------------------------
# Tenant isolation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_dashboard_does_not_leak_other_org_data(org, program):
    other_org = Organization.objects.create(name="Other", slug="other-cd")
    other_program = Program.all_objects.create(
        organization=other_org,
        name="Other Summer",
        slug="other-summer",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )
    other_user = User.objects.create_user(email="other@cd.test", password="pw")
    other_person = Person.all_objects.create(
        organization=other_org, first_name="Other", last_name="Counselor", user=other_user,
    )
    Membership.all_objects.create(
        program=other_program, person=other_person, role="counselor", is_active=True,
    )
    # An order in *org* must not appear for the user in *other_org*.
    counselor_person_obj = Person.all_objects.create(
        organization=org, first_name="X", last_name="Y",
    )
    counselor_membership_obj = Membership.all_objects.create(
        program=program, person=counselor_person_obj, role="counselor", is_active=True,
    )
    Order.all_objects.create(
        organization=org,
        program=program,
        submitted_by=counselor_membership_obj,
        item="cross-org item",
        status="new",
    )
    c = _client(other_user, other_org)
    with organization_context(other_org):
        resp = c.get("/api/v1/counselor/dashboard/?nocache=1")
    assert resp.data["sections"]["requests"]["open_count"] == 0


# ---------------------------------------------------------------------------
# Story 2 criterion 4: rollover hour reflected in payload
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_dashboard_returns_rollover_hour_and_timezone(
    org, program, counselor_user, counselor_person, counselor_membership,
):
    org.settings = {"rollover_hour": 5, "timezone": "America/Chicago"}
    org.save()
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/counselor/dashboard/?nocache=1")
    assert resp.data["rollover_hour"] == 5
    assert resp.data["timezone"] == "America/Chicago"
