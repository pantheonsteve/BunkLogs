"""Tests for counselor camper reflection write endpoints (Step 7_6c).

Covers ``POST /api/v1/counselor/camper-reflections/`` and
``PATCH /api/v1/counselor/camper-reflections/<id>/`` against Story 3 + 4
acceptance criteria: idempotency, off-camp gating, cross-counselor edit
permission, audit emission, edit window enforcement.
"""
from __future__ import annotations

import uuid
from datetime import date
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import AuditEvent
from bunk_logs.core.models import CamperDayState
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate

User = get_user_model()

CAMPER_SCHEMA = {
    "fields": [
        {"key": "note", "type": "textarea", "required": False, "prompts": {"en": "Notes"}},
    ],
}


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def org(db):
    return Organization.objects.create(name="CW Camp", slug="cw-camp")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="CW Camp Summer 2026",
        slug="cw-summer-2026",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def counselor_user():
    return User.objects.create_user(email="counselor@cw.test", password="pw")


@pytest.fixture
def counselor_person(org, counselor_user):
    return Person.all_objects.create(
        organization=org, first_name="Mira", last_name="Silver", user=counselor_user,
    )


@pytest.fixture
def counselor_membership(program, counselor_person):
    return Membership.all_objects.create(
        program=program, person=counselor_person, role="counselor", is_active=True,
    )


@pytest.fixture
def bunk(org, program):
    return AssignmentGroup.objects.create(
        organization=org, program=program, name="Bunk Birch",
        slug="bunk-birch-cw", group_type="bunk", is_active=True,
    )


@pytest.fixture
def counselor_as_author(bunk, counselor_person):
    return AssignmentGroupMembership.objects.create(
        group=bunk, person=counselor_person, role_in_group="author", is_active=True,
    )


@pytest.fixture
def campers(org, bunk):
    persons = []
    for first, last in [("Sarah", "Levin"), ("Maya", "Cohen")]:
        p = Person.all_objects.create(organization=org, first_name=first, last_name=last)
        AssignmentGroupMembership.objects.create(
            group=bunk, person=p, role_in_group="subject", is_active=True,
        )
        persons.append(p)
    return persons


@pytest.fixture
def camper_template(org):
    return ReflectionTemplate.all_objects.create(
        organization=org, name="Bunk Log", slug="bunk-log-cw",
        cadence="daily", subject_mode="single_subject",
        assignment_scope="per_subject_in_group",
        assignment_group_types=["bunk"], schema=CAMPER_SCHEMA,
        languages=["en"], is_active=True, program_type="summer_camp",
        author_role_filter=["counselor"], supports_privacy=True,
    )


def _client(user, org):
    c = APIClient()
    c.force_authenticate(user=user)
    c.credentials(HTTP_X_ORGANIZATION_SLUG=org.slug)
    return c


def _post_payload(*, subject, bunk, csid=None):
    return {
        "subject_id": subject.id,
        "assignment_group_id": bunk.id,
        "answers": {"note": "Great day"},
        "language": "en",
        "client_submission_id": str(csid or uuid.uuid4()),
    }


# ---------------------------------------------------------------------------
# Auth / context
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_post_requires_authentication():
    c = APIClient()
    resp = c.post("/api/v1/counselor/camper-reflections/", {}, format="json")
    assert resp.status_code in {401, 403}


@pytest.mark.django_db
def test_post_requires_org_context(counselor_user):
    c = APIClient()
    c.force_authenticate(user=counselor_user)
    resp = c.post("/api/v1/counselor/camper-reflections/", {}, format="json")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Successful create
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_create_camper_reflection_201_and_persists(
    org, program, counselor_user, counselor_person, counselor_membership,
    bunk, counselor_as_author, campers, camper_template,
):
    sarah = campers[0]
    c = _client(counselor_user, org)
    payload = _post_payload(subject=sarah, bunk=bunk)
    with organization_context(org):
        resp = c.post("/api/v1/counselor/camper-reflections/", payload, format="json")
    assert resp.status_code == 201, resp.data
    assert resp.data["subject_id"] == sarah.id
    assert resp.data["assignment_group_id"] == bunk.id
    assert resp.data["template"]["slug"] == "bunk-log-cw"
    assert resp.data["client_submission_id"] == payload["client_submission_id"]
    assert resp.data["audience"]  # AudienceDisclosure roles surfaced
    assert "Counselor" in resp.data["audience"]
    row = Reflection.all_objects.get(id=resp.data["id"])
    assert row.author == counselor_person
    assert row.is_complete is True


@pytest.mark.django_db
def test_create_emits_audit_created(
    org, program, counselor_user, counselor_person, counselor_membership,
    bunk, counselor_as_author, campers, camper_template,
):
    sarah = campers[0]
    c = _client(counselor_user, org)
    with organization_context(org):
        c.post(
            "/api/v1/counselor/camper-reflections/",
            _post_payload(subject=sarah, bunk=bunk),
            format="json",
        )
    events = AuditEvent.all_objects.filter(content_type="reflection")
    assert events.filter(event_type=AuditEvent.EventType.CREATED).exists()


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_create_is_idempotent_on_client_submission_id(
    org, program, counselor_user, counselor_person, counselor_membership,
    bunk, counselor_as_author, campers, camper_template,
):
    sarah = campers[0]
    c = _client(counselor_user, org)
    csid = uuid.uuid4()
    payload = _post_payload(subject=sarah, bunk=bunk, csid=csid)
    with organization_context(org):
        first = c.post("/api/v1/counselor/camper-reflections/", payload, format="json")
        second = c.post("/api/v1/counselor/camper-reflections/", payload, format="json")
    assert first.status_code == 201
    assert second.status_code == 200
    assert first.data["id"] == second.data["id"]
    assert Reflection.all_objects.filter(client_submission_id=csid).count() == 1


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_non_author_on_bunk_cannot_post(
    org, program, counselor_user, counselor_person, counselor_membership,
    bunk, campers, camper_template,
):
    # No counselor_as_author fixture pulled in => viewer is not an author.
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.post(
            "/api/v1/counselor/camper-reflections/",
            _post_payload(subject=campers[0], bunk=bunk),
            format="json",
        )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_subject_must_be_on_bunk(
    org, program, counselor_user, counselor_person, counselor_membership,
    bunk, counselor_as_author, campers, camper_template,
):
    stranger = Person.all_objects.create(
        organization=org, first_name="Off", last_name="Roster",
    )
    c = _client(counselor_user, org)
    payload = _post_payload(subject=stranger, bunk=bunk)
    with organization_context(org):
        resp = c.post("/api/v1/counselor/camper-reflections/", payload, format="json")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_off_camp_camper_rejected(
    org, program, counselor_user, counselor_person, counselor_membership,
    bunk, counselor_as_author, campers, camper_template,
):
    sarah = campers[0]
    CamperDayState.all_objects.create(
        organization=org, program=program, camper=sarah,
        date=date.today(), is_off_camp=True,
    )
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.post(
            "/api/v1/counselor/camper-reflections/",
            _post_payload(subject=sarah, bunk=bunk),
            format="json",
        )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# PATCH / edit window / cross-counselor permission
# ---------------------------------------------------------------------------


@pytest.fixture
def existing_reflection(
    org, program, counselor_person, bunk, counselor_as_author, campers, camper_template,
):
    today = date.today()
    return Reflection.all_objects.create(
        organization=org, program=program, subject=campers[0],
        author=counselor_person, assignment_group=bunk, template=camper_template,
        period_start=today, period_end=today,
        answers={"note": "initial"}, language="en", is_complete=True,
        client_submission_id=uuid.uuid4(),
    )


@pytest.mark.django_db
def test_patch_updates_answers_and_emits_audit(
    org, counselor_user, counselor_membership, existing_reflection,
):
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.patch(
            f"/api/v1/counselor/camper-reflections/{existing_reflection.id}/",
            {"answers": {"note": "updated"}}, format="json",
        )
    assert resp.status_code == 200, resp.data
    existing_reflection.refresh_from_db()
    assert existing_reflection.answers == {"note": "updated"}
    assert AuditEvent.all_objects.filter(
        content_type="reflection",
        event_type=AuditEvent.EventType.EDITED,
        content_id=str(existing_reflection.id),
    ).exists()


@pytest.mark.django_db
def test_co_counselor_on_same_bunk_can_edit(
    org, program, bunk, counselor_person, existing_reflection, camper_template,
):
    """Story 4 criterion 2: any active bunk author can edit, not just author."""
    co_user = User.objects.create_user(email="co@cw.test", password="pw")
    co_person = Person.all_objects.create(
        organization=org, first_name="Jordan", last_name="Patel", user=co_user,
    )
    Membership.all_objects.create(
        program=program, person=co_person, role="counselor", is_active=True,
    )
    AssignmentGroupMembership.objects.create(
        group=bunk, person=co_person, role_in_group="author", is_active=True,
    )
    c = _client(co_user, org)
    with organization_context(org):
        resp = c.patch(
            f"/api/v1/counselor/camper-reflections/{existing_reflection.id}/",
            {"answers": {"note": "co edited"}}, format="json",
        )
    assert resp.status_code == 200, resp.data
    existing_reflection.refresh_from_db()
    assert existing_reflection.answers == {"note": "co edited"}


@pytest.mark.django_db
def test_unrelated_counselor_cannot_edit(
    org, program, bunk, existing_reflection,
):
    """A counselor not on the bunk gets 403."""
    stranger_user = User.objects.create_user(email="stranger@cw.test", password="pw")
    stranger_person = Person.all_objects.create(
        organization=org, first_name="Stranger", last_name="X", user=stranger_user,
    )
    Membership.all_objects.create(
        program=program, person=stranger_person, role="counselor", is_active=True,
    )
    c = _client(stranger_user, org)
    with organization_context(org):
        resp = c.patch(
            f"/api/v1/counselor/camper-reflections/{existing_reflection.id}/",
            {"answers": {"note": "no"}}, format="json",
        )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_patch_outside_edit_window_returns_403(
    org, program, counselor_person, counselor_user, counselor_membership,
    bunk, counselor_as_author, campers, camper_template,
):
    yesterday = date.today() - timedelta(days=1)
    old = Reflection.all_objects.create(
        organization=org, program=program, subject=campers[0],
        author=counselor_person, assignment_group=bunk, template=camper_template,
        period_start=yesterday, period_end=yesterday,
        answers={"note": "old"}, language="en", is_complete=True,
        client_submission_id=uuid.uuid4(),
    )
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.patch(
            f"/api/v1/counselor/camper-reflections/{old.id}/",
            {"answers": {"note": "late"}}, format="json",
        )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Cache invalidation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_post_invalidates_dashboard_cache(
    org, program, counselor_user, counselor_person, counselor_membership,
    bunk, counselor_as_author, campers, camper_template,
):
    c = _client(counselor_user, org)
    with organization_context(org):
        # Prime the cache by hitting the dashboard.
        c.get("/api/v1/counselor/dashboard/")
        # Submit a reflection — should invalidate the prior cache.
        c.post(
            "/api/v1/counselor/camper-reflections/",
            _post_payload(subject=campers[0], bunk=bunk),
            format="json",
        )
        # Fresh GET should reflect the new submission in covered count.
        resp = c.get("/api/v1/counselor/dashboard/")
    section = resp.data["sections"]["camper_reflections"]
    assert section["covered"] == 1
