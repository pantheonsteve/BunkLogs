"""API tests for Admin People dedupe."""

from __future__ import annotations

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import AuditEvent
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
def api() -> APIClient:
    return APIClient()


@pytest.fixture
def org():
    return Organization.objects.create(name="Dedupe Org", slug="dedupe-org")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="Dedupe Org Summer",
        slug="summer",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def admin_user(org, program):
    user = User.objects.create_user(email="admin-dedupe@example.com", password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="Ad", last_name="Min", user=user,
    )
    Membership.all_objects.create(program=program, person=person, role="admin", is_active=True)
    return user


@pytest.fixture
def non_admin_user(org, program):
    user = User.objects.create_user(email="other-dedupe@example.com", password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="Co", last_name="Un", user=user,
    )
    Membership.all_objects.create(program=program, person=person, role="counselor", is_active=True)
    return user


class TestAdminPeopleDedupe:
    PREVIEW_URL = "/api/v1/admin/people/dedupe/preview/"
    APPLY_URL = "/api/v1/admin/people/dedupe/"

    def test_non_admin_blocked(self, api, org, non_admin_user):
        api.force_authenticate(user=non_admin_user)
        with organization_context(org):
            response = api.post(
                self.PREVIEW_URL,
                {"winner_id": 1, "losers": [{"person_id": 2, "strategy": "repoint"}]},
                format="json",
                **_hdr(org.slug),
            )
        assert response.status_code == 403

    def test_preview_and_apply_repoint_merge(self, api, org, program, admin_user):
        winner = Person.all_objects.create(
            organization=org,
            first_name="Win",
            last_name="Ner",
            external_ids={"campminder_id": "123"},
        )
        loser = Person.all_objects.create(
            organization=org,
            first_name="Los",
            last_name="Er",
        )
        Membership.all_objects.create(program=program, person=loser, role="counselor")

        api.force_authenticate(user=admin_user)
        payload = {
            "winner_id": winner.id,
            "losers": [{"person_id": loser.id, "strategy": "repoint"}],
        }
        with organization_context(org):
            preview = api.post(self.PREVIEW_URL, payload, format="json", **_hdr(org.slug))
        assert preview.status_code == 200, preview.content
        assert preview.json()["ok"] is True
        assert preview.json()["plans"][0]["strategy"] == "repoint"

        apply_payload = {**payload, "reason": "Duplicate legacy import"}
        with organization_context(org):
            applied = api.post(self.APPLY_URL, apply_payload, format="json", **_hdr(org.slug))
        assert applied.status_code == 200, applied.content
        assert not Person.all_objects.filter(pk=loser.id).exists()
        assert Membership.all_objects.filter(person=winner, role="counselor").exists()
        assert AuditEvent.all_objects.filter(content_type="person_dedupe").exists()

    def test_apply_requires_force_user_when_users_conflict(self, api, org, admin_user):
        winner_user = User.objects.create_user(email="winner@example.com", password="pw")
        loser_user = User.objects.create_user(email="loser@example.com", password="pw")
        winner = Person.all_objects.create(
            organization=org, first_name="Win", last_name="Ner", user=winner_user,
        )
        loser = Person.all_objects.create(
            organization=org, first_name="Los", last_name="Er", user=loser_user,
        )

        api.force_authenticate(user=admin_user)
        payload = {
            "winner_id": winner.id,
            "losers": [{"person_id": loser.id, "strategy": "repoint"}],
            "reason": "Duplicate login",
        }
        with organization_context(org):
            blocked = api.post(self.APPLY_URL, payload, format="json", **_hdr(org.slug))
        assert blocked.status_code == 409

        payload["losers"][0]["force_user"] = True
        with organization_context(org):
            applied = api.post(self.APPLY_URL, payload, format="json", **_hdr(org.slug))
        assert applied.status_code == 200, applied.content
        winner.refresh_from_db()
        assert winner.user_id == winner_user.id
        assert not Person.all_objects.filter(pk=loser.id).exists()

    def test_discard_blocked_without_confirm_destructive(self, api, org, program, admin_user):
        person = Person.all_objects.create(
            organization=org, first_name="Cam", last_name="Per",
        )
        author = Person.all_objects.create(
            organization=org, first_name="Auth", last_name="Or",
        )
        winner = Person.all_objects.create(
            organization=org, first_name="Keep", last_name="Er",
        )
        template = ReflectionTemplate.all_objects.create(
            organization=org,
            name="Dedupe Org Daily",
            slug="daily",
            cadence="daily",
            schema={"fields": []},
        )
        Reflection.all_objects.create(
            organization=org,
            program=program,
            subject=person,
            author=author,
            template=template,
            period_start=date(2026, 7, 1),
            period_end=date(2026, 7, 7),
            answers={},
        )

        api.force_authenticate(user=admin_user)
        payload = {
            "winner_id": winner.id,
            "losers": [{"person_id": person.id, "strategy": "discard"}],
            "reason": "Remove duplicate",
        }
        with organization_context(org):
            blocked = api.post(self.APPLY_URL, payload, format="json", **_hdr(org.slug))
        assert blocked.status_code == 409

        payload["confirm_destructive"] = True
        with organization_context(org):
            applied = api.post(self.APPLY_URL, payload, format="json", **_hdr(org.slug))
        assert applied.status_code == 200, applied.content
        assert not Person.all_objects.filter(pk=person.id).exists()
