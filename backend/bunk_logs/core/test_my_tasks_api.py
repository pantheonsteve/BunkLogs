"""Tests for the my-tasks and supervisor-coverage API endpoints (prompt 3.19)."""
from __future__ import annotations

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate

User = get_user_model()

# ---------------------------------------------------------------------------
# Minimal schema helpers
# ---------------------------------------------------------------------------

SIMPLE_SCHEMA = {
    "fields": [
        {
            "key": "note",
            "type": "textarea",
            "required": False,
            "prompts": {"en": "Notes"},
        },
    ],
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Tasks Test Org", slug="tasks-org")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="Tasks Test Org Summer 2026",
        slug="tasks-summer-2026",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def counselor_user(org):
    return User.objects.create_user(email="counselor_tasks@test.com", password="pw")


@pytest.fixture
def counselor_person(org, counselor_user):
    return Person.all_objects.create(
        organization=org,
        first_name="Counselor",
        last_name="Mike",
        user=counselor_user,
    )


@pytest.fixture
def counselor_membership(program, counselor_person):
    return Membership.all_objects.create(
        program=program,
        person=counselor_person,
        role="counselor",
        is_active=True,
    )


@pytest.fixture
def self_template(org):
    return ReflectionTemplate.all_objects.create(
        organization=org,
        name="Daily Self Check",
        slug="self-check-319",
        cadence="daily",
        schema=SIMPLE_SCHEMA,
        languages=["en"],
        subject_mode="self",
        author_role_filter=["counselor"],
        is_active=True,
    )


@pytest.fixture
def bunk_group(org, program):
    return AssignmentGroup.objects.create(
        organization=org,
        program=program,
        name="Bunk Maple",
        slug="bunk-maple-319",
        group_type="bunk",
        is_active=True,
    )


@pytest.fixture
def camper_person(org):
    return Person.all_objects.create(
        organization=org,
        first_name="Sarah",
        last_name="Levin",
    )


@pytest.fixture
def camper_person2(org):
    return Person.all_objects.create(
        organization=org,
        first_name="Maya",
        last_name="Cohen",
    )


@pytest.fixture
def roster_template(org):
    return ReflectionTemplate.all_objects.create(
        organization=org,
        name="Bunk Log",
        slug="bunk-log-319",
        cadence="daily",
        schema=SIMPLE_SCHEMA,
        languages=["en"],
        subject_mode="single_subject",
        assignment_group_types=["bunk"],
        author_role_filter=["counselor"],
        is_active=True,
    )


@pytest.fixture
def counselor_as_author(bunk_group, counselor_person):
    return AssignmentGroupMembership.objects.create(
        group=bunk_group,
        person=counselor_person,
        role_in_group="author",
        is_active=True,
    )


@pytest.fixture
def camper_in_bunk(bunk_group, camper_person):
    return AssignmentGroupMembership.objects.create(
        group=bunk_group,
        person=camper_person,
        role_in_group="subject",
        is_active=True,
    )


@pytest.fixture
def camper2_in_bunk(bunk_group, camper_person2):
    return AssignmentGroupMembership.objects.create(
        group=bunk_group,
        person=camper_person2,
        role_in_group="subject",
        is_active=True,
    )


def _authed_client(user, org):
    """Return an API client authenticated as user with org context."""
    client = APIClient()
    client.force_authenticate(user=user)
    client.credentials(HTTP_X_ORGANIZATION_SLUG=org.slug)
    return client


# ---------------------------------------------------------------------------
# my-tasks: self-reflection
# ---------------------------------------------------------------------------


def _drop_seeded_counselor_self_template():
    """Strip the seeded global counselor self-reflection template.

    These tests pre-date the migration 0029 seed and assert specific task
    counts / templates by index; the global template adds an extra row that
    isn't relevant to my-tasks behavior under test.
    """
    ReflectionTemplate.all_objects.filter(
        organization__isnull=True, slug="counselor-self-reflection",
    ).delete()


@pytest.mark.django_db
def test_my_tasks_self_reflection_appears(
    org, program, counselor_user, counselor_person, counselor_membership, self_template,
):
    _drop_seeded_counselor_self_template()
    with organization_context(org):
        client = _authed_client(counselor_user, org)
        resp = client.get("/api/v1/reflections/my-tasks/")

    assert resp.status_code == 200
    tasks = resp.data["tasks"]
    assert len(tasks) == 1
    task = tasks[0]
    assert task["subject_mode"] == "self"
    assert task["template"]["slug"] == "self-check-319"
    assert task["self_status"]["submitted"] is False
    assert task["completion"]["total"] == 1
    assert task["completion"]["covered"] == 0


@pytest.mark.django_db
def test_my_tasks_self_reflection_shows_submitted(
    org, program, counselor_user, counselor_person, counselor_membership, self_template,
):
    _drop_seeded_counselor_self_template()
    today = date.today()
    with organization_context(org):
        Reflection.all_objects.create(
            organization=org,
            program=program,
            author=counselor_person,
            subject=counselor_person,
            template=self_template,
            period_start=today,
            period_end=today,
            answers={"note": "Good day"},
            language="en",
        )
        client = _authed_client(counselor_user, org)
        resp = client.get("/api/v1/reflections/my-tasks/")

    assert resp.status_code == 200
    task = resp.data["tasks"][0]
    assert task["self_status"]["submitted"] is True
    assert task["completion"]["covered"] == 1


@pytest.mark.django_db
def test_my_tasks_no_membership_no_tasks(org, counselor_user, counselor_person, self_template):
    # counselor_person exists but has no membership — should see no tasks
    with organization_context(org):
        client = _authed_client(counselor_user, org)
        resp = client.get("/api/v1/reflections/my-tasks/")

    assert resp.status_code == 200
    assert resp.data["tasks"] == []


# ---------------------------------------------------------------------------
# my-tasks: roster (single_subject) mode
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_my_tasks_roster_shows_subjects(
    org,
    program,
    counselor_user,
    counselor_person,
    counselor_membership,
    roster_template,
    bunk_group,
    counselor_as_author,
    camper_in_bunk,
    camper2_in_bunk,
    camper_person,
    camper_person2,
):
    _drop_seeded_counselor_self_template()
    with organization_context(org):
        client = _authed_client(counselor_user, org)
        resp = client.get("/api/v1/reflections/my-tasks/")

    assert resp.status_code == 200
    tasks = resp.data["tasks"]
    assert len(tasks) == 1
    task = tasks[0]
    assert task["subject_mode"] == "single_subject"
    assert task["assignment_group"]["name"] == "Bunk Maple"
    assert task["completion"]["total"] == 2
    assert task["completion"]["covered"] == 0
    subject_names = {s["name"] for s in task["subjects"]}
    assert "Sarah Levin" in subject_names
    assert "Maya Cohen" in subject_names


@pytest.mark.django_db
def test_my_tasks_coverage_state_reflects_existing_reflections(
    org,
    program,
    counselor_user,
    counselor_person,
    counselor_membership,
    roster_template,
    bunk_group,
    counselor_as_author,
    camper_in_bunk,
    camper2_in_bunk,
    camper_person,
    camper_person2,
):
    today = date.today()
    with organization_context(org):
        Reflection.all_objects.create(
            organization=org,
            program=program,
            author=counselor_person,
            subject=camper_person,
            assignment_group=bunk_group,
            template=roster_template,
            period_start=today,
            period_end=today,
            answers={"note": "Great"},
            language="en",
        )
        client = _authed_client(counselor_user, org)
        resp = client.get("/api/v1/reflections/my-tasks/")

    assert resp.status_code == 200
    task = resp.data["tasks"][0]
    assert task["completion"]["covered"] == 1
    assert task["completion"]["my_count"] == 1

    sarah = next(s for s in task["subjects"] if s["name"] == "Sarah Levin")
    assert sarah["covered"] is True
    assert sarah["covered_by_me"] is True

    maya = next(s for s in task["subjects"] if s["name"] == "Maya Cohen")
    assert maya["covered"] is False
    assert maya["covered_by_me"] is False


@pytest.mark.django_db
def test_my_tasks_covered_by_me_flag_accurate(
    org,
    program,
    counselor_user,
    counselor_person,
    counselor_membership,
    roster_template,
    bunk_group,
    counselor_as_author,
    camper_in_bunk,
    camper_person,
):
    """covered_by_me is False when another counselor logged the camper."""
    _drop_seeded_counselor_self_template()
    other_user = User.objects.create_user(email="other_counselor@test.com", password="pw")
    other_person = Person.all_objects.create(
        organization=org, first_name="Other", last_name="Counselor", user=other_user,
    )
    today = date.today()
    with organization_context(org):
        Reflection.all_objects.create(
            organization=org,
            program=program,
            author=other_person,
            subject=camper_person,
            assignment_group=bunk_group,
            template=roster_template,
            period_start=today,
            period_end=today,
            answers={"note": "ok"},
            language="en",
        )
        client = _authed_client(counselor_user, org)
        resp = client.get("/api/v1/reflections/my-tasks/")

    task = resp.data["tasks"][0]
    sarah = next(s for s in task["subjects"] if s["name"] == "Sarah Levin")
    assert sarah["covered"] is True
    assert sarah["covered_by_me"] is False


# ---------------------------------------------------------------------------
# my-tasks: multi-bunk counselor sees both bunks
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_my_tasks_multi_bunk_counselor_sees_both_bunks(
    org,
    program,
    counselor_user,
    counselor_person,
    counselor_membership,
    roster_template,
    bunk_group,
    counselor_as_author,
    camper_in_bunk,
):
    _drop_seeded_counselor_self_template()
    bunk2 = AssignmentGroup.objects.create(
        organization=org,
        program=program,
        name="Bunk Oak",
        slug="bunk-oak-319",
        group_type="bunk",
        is_active=True,
    )
    AssignmentGroupMembership.objects.create(
        group=bunk2,
        person=counselor_person,
        role_in_group="author",
        is_active=True,
    )
    camper3 = Person.all_objects.create(organization=org, first_name="Eden", last_name="R")
    AssignmentGroupMembership.objects.create(
        group=bunk2,
        person=camper3,
        role_in_group="subject",
        is_active=True,
    )
    with organization_context(org):
        client = _authed_client(counselor_user, org)
        resp = client.get("/api/v1/reflections/my-tasks/")

    tasks = resp.data["tasks"]
    group_names = {t["assignment_group"]["name"] for t in tasks}
    assert "Bunk Maple" in group_names
    assert "Bunk Oak" in group_names


# ---------------------------------------------------------------------------
# supervisor-coverage
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_supervisor_coverage_scopes_to_author_groups(
    org,
    program,
    counselor_user,
    counselor_person,
    counselor_membership,
    roster_template,
    bunk_group,
    counselor_as_author,
    camper_in_bunk,
    camper2_in_bunk,
):
    with organization_context(org):
        client = _authed_client(counselor_user, org)
        resp = client.get("/api/v1/reflections/supervisor-coverage/")

    assert resp.status_code == 200
    groups = resp.data["groups"]
    assert len(groups) == 1
    g = groups[0]
    assert g["name"] == "Bunk Maple"
    assert len(g["template_coverage"]) == 1
    tc = g["template_coverage"][0]
    assert tc["total"] == 2
    assert tc["covered"] == 0
    assert tc["percent"] == 0


@pytest.mark.django_db
def test_supervisor_coverage_no_groups_returns_empty(db, org):
    counselor_user = User.objects.create_user(email="cov_empty@test.com", password="pw")
    Person.all_objects.create(
        organization=org, first_name="Solo", last_name="Counselor", user=counselor_user,
    )
    with organization_context(org):
        client = _authed_client(counselor_user, org)
        resp = client.get("/api/v1/reflections/supervisor-coverage/")

    assert resp.status_code == 200
    assert resp.data["groups"] == []


# ---------------------------------------------------------------------------
# Reflection create: roster-mode submission
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_create_reflection_with_subject_and_assignment_group(
    org,
    program,
    counselor_user,
    counselor_person,
    counselor_membership,
    roster_template,
    bunk_group,
    counselor_as_author,
    camper_in_bunk,
    camper_person,
):
    today = date.today()
    with organization_context(org):
        client = _authed_client(counselor_user, org)
        resp = client.post(
            "/api/v1/reflections/",
            {
                "program_slug": program.slug,
                "template": roster_template.id,
                "subject": camper_person.id,
                "assignment_group": bunk_group.id,
                "period_start": today.isoformat(),
                "period_end": today.isoformat(),
                "answers": {"note": "Doing well"},
                "language": "en",
            },
            format="json",
        )

    assert resp.status_code == 201
    assert resp.data["author"] == counselor_person.id
    assert resp.data["subject"] == camper_person.id
    assert resp.data["assignment_group"] == bunk_group.id


@pytest.mark.django_db
def test_create_reflection_roster_rejects_non_author(
    org,
    program,
    counselor_user,
    counselor_person,
    counselor_membership,
    roster_template,
    bunk_group,
    camper_person,
):
    """A user who is not an author in the group cannot submit using that group."""
    today = date.today()
    with organization_context(org):
        client = _authed_client(counselor_user, org)
        resp = client.post(
            "/api/v1/reflections/",
            {
                "program_slug": program.slug,
                "template": roster_template.id,
                "subject": camper_person.id,
                "assignment_group": bunk_group.id,
                "period_start": today.isoformat(),
                "period_end": today.isoformat(),
                "answers": {"note": "test"},
                "language": "en",
            },
            format="json",
        )

    assert resp.status_code == 400
