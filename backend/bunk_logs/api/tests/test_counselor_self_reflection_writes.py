"""Tests for counselor self-reflection write endpoints (Step 7_6c).

Covers ``POST /api/v1/counselor/self-reflection/`` and
``PATCH /api/v1/counselor/self-reflection/<id>/`` against Story 5 + 6
acceptance criteria including the ``day_off`` shortcut.
"""
from __future__ import annotations

import uuid
from datetime import date
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

from bunk_logs.api.counselor.common import counselor_self_template
from bunk_logs.core.context import organization_context
from bunk_logs.core.models import AuditEvent
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection

User = get_user_model()


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def org(db):
    return Organization.objects.create(name="SR Camp", slug="sr-camp")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org, name="SR Camp Summer 2026", slug="sr-summer-2026",
        program_type="summer_camp",
        start_date=date(2026, 6, 1), end_date=date(2026, 8, 31),
    )


@pytest.fixture
def counselor_user():
    return User.objects.create_user(email="counselor@sr.test", password="pw")


@pytest.fixture
def counselor_person(org, counselor_user):
    return Person.all_objects.create(
        organization=org, first_name="Aviv", last_name="Lev", user=counselor_user,
    )


@pytest.fixture
def counselor_membership(program, counselor_person):
    return Membership.all_objects.create(
        program=program, person=counselor_person, role="counselor", is_active=True,
    )


def _client(user, org):
    c = APIClient()
    c.force_authenticate(user=user)
    c.credentials(HTTP_X_ORGANIZATION_SLUG=org.slug)
    return c


# ---------------------------------------------------------------------------
# day_off shortcut (Story 5 criterion 3)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_day_off_shortcut_creates_minimal_reflection(
    org, counselor_user, counselor_person, counselor_membership,
):
    c = _client(counselor_user, org)
    payload = {"day_off": True, "client_submission_id": str(uuid.uuid4())}
    with organization_context(org):
        resp = c.post("/api/v1/counselor/self-reflection/", payload, format="json")
    assert resp.status_code == 201, resp.data
    assert resp.data["answers"] == {"day_off": True}
    row = Reflection.all_objects.get(id=resp.data["id"])
    assert row.is_complete is True
    assert row.author == counselor_person
    assert row.subject == counselor_person


@pytest.mark.django_db
def test_full_answers_create_validates_against_schema(
    org, counselor_user, counselor_person, counselor_membership,
):
    c = _client(counselor_user, org)
    payload = {
        "answers": {
            "day_off": False,
            "overall_day": 4,
            "wins": ["Helped a camper through homesickness"],
            "improvements": ["More water during free swim"],
            "concern": "Camper Eden seemed quiet today.",
        },
        "language": "en",
        "client_submission_id": str(uuid.uuid4()),
    }
    with organization_context(org):
        resp = c.post("/api/v1/counselor/self-reflection/", payload, format="json")
    assert resp.status_code == 201, resp.data
    assert resp.data["answers"]["overall_day"] == 4


# ---------------------------------------------------------------------------
# Idempotency + audit
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_self_reflection_idempotent(
    org, counselor_user, counselor_person, counselor_membership,
):
    c = _client(counselor_user, org)
    csid = str(uuid.uuid4())
    payload = {"day_off": True, "client_submission_id": csid}
    with organization_context(org):
        first = c.post("/api/v1/counselor/self-reflection/", payload, format="json")
        second = c.post("/api/v1/counselor/self-reflection/", payload, format="json")
    assert first.status_code == 201
    assert second.status_code == 200
    assert first.data["id"] == second.data["id"]
    assert Reflection.all_objects.filter(
        client_submission_id=uuid.UUID(csid),
    ).count() == 1


@pytest.mark.django_db
def test_self_reflection_emits_audit(
    org, counselor_user, counselor_person, counselor_membership,
):
    c = _client(counselor_user, org)
    with organization_context(org):
        c.post(
            "/api/v1/counselor/self-reflection/",
            {"day_off": True, "client_submission_id": str(uuid.uuid4())},
            format="json",
        )
    assert AuditEvent.all_objects.filter(
        event_type=AuditEvent.EventType.CREATED, content_type="reflection",
    ).exists()


# ---------------------------------------------------------------------------
# PATCH / edit window / permission
# ---------------------------------------------------------------------------


@pytest.fixture
def existing_self(org, counselor_person, counselor_membership, db):
    # We rely on the migration-seeded global template. The resolver uses
    # the org-scoped Membership manager so it must run inside the org
    # context to find the viewer's active memberships.
    with organization_context(org):
        template = counselor_self_template(
            counselor_person, org, counselor_membership.program,
        )
    today = date.today()
    return Reflection.all_objects.create(
        organization=org, program=counselor_membership.program,
        author=counselor_person, subject=counselor_person, template=template,
        period_start=today, period_end=today,
        answers={"day_off": True}, language="en", is_complete=True,
        client_submission_id=uuid.uuid4(),
    )


@pytest.mark.django_db
def test_patch_self_reflection_updates_and_audits(
    org, counselor_user, existing_self,
):
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.patch(
            f"/api/v1/counselor/self-reflection/{existing_self.id}/",
            {"day_off": False, "answers": {
                "day_off": False, "overall_day": 5,
                "wins": [], "improvements": [], "concern": "",
            }}, format="json",
        )
    assert resp.status_code == 200, resp.data
    existing_self.refresh_from_db()
    assert existing_self.answers["overall_day"] == 5
    assert AuditEvent.all_objects.filter(
        event_type=AuditEvent.EventType.EDITED, content_type="reflection",
        content_id=str(existing_self.id),
    ).exists()


@pytest.mark.django_db
def test_patch_other_users_self_reflection_403(
    org, program, counselor_user, existing_self,
):
    other_user = User.objects.create_user(email="other@sr.test", password="pw")
    other_person = Person.all_objects.create(
        organization=org, first_name="Other", last_name="P", user=other_user,
    )
    Membership.all_objects.create(
        program=program, person=other_person, role="counselor", is_active=True,
    )
    c = _client(other_user, org)
    with organization_context(org):
        resp = c.patch(
            f"/api/v1/counselor/self-reflection/{existing_self.id}/",
            {"day_off": False, "answers": {"day_off": False, "overall_day": 3,
                "wins": [], "improvements": [], "concern": ""}},
            format="json",
        )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_patch_outside_edit_window_403(
    org, counselor_user, counselor_person, counselor_membership,
):
    with organization_context(org):
        template = counselor_self_template(
            counselor_person, org, counselor_membership.program,
        )
    yesterday = date.today() - timedelta(days=1)
    row = Reflection.all_objects.create(
        organization=org, program=counselor_membership.program,
        author=counselor_person, subject=counselor_person, template=template,
        period_start=yesterday, period_end=yesterday,
        answers={"day_off": True}, language="en", is_complete=True,
        client_submission_id=uuid.uuid4(),
    )
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.patch(
            f"/api/v1/counselor/self-reflection/{row.id}/",
            {"day_off": False, "answers": {"day_off": False, "overall_day": 3,
                "wins": [], "improvements": [], "concern": ""}},
            format="json",
        )
    assert resp.status_code == 403
