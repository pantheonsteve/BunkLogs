"""API tests for admin Person delete preview/apply."""

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
    return Organization.objects.create(name="Delete Org", slug="delete-org")


@pytest.fixture
def program(org):
    from datetime import date as d

    return Program.all_objects.create(
        organization=org,
        name="Delete Org Summer",
        slug="delete-org-summer",
        program_type="summer_camp",
        start_date=d(2026, 6, 1),
        end_date=d(2026, 8, 31),
    )


@pytest.fixture
def admin_user(org, program):
    u = User.objects.create_user(email="admin-delete@example.com", password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="Ad", last_name="Min", user=u,
    )
    Membership.all_objects.create(
        program=program, person=person, role="admin", is_active=True,
    )
    return u


class TestAdminPersonDelete:
    def test_non_admin_blocked(self, api, org, program):
        u = User.objects.create_user(email="other-delete@example.com", password="pw")
        person = Person.all_objects.create(
            organization=org, first_name="Co", last_name="Un", user=u,
        )
        Membership.all_objects.create(
            program=program, person=person, role="counselor", is_active=True,
        )
        target = Person.all_objects.create(
            organization=org, first_name="Tar", last_name="Get",
        )
        api.force_authenticate(user=u)
        with organization_context(org):
            r = api.post(
                f"/api/v1/admin/people/{target.id}/delete/preview/",
                {},
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 403

    def test_delete_person(self, api, org, program, admin_user):
        target = Person.all_objects.create(
            organization=org, first_name="Dup", last_name="Licate", email="dup@example.com",
        )
        Membership.all_objects.create(
            program=program, person=target, role="counselor", is_active=True,
        )
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            preview = api.post(
                f"/api/v1/admin/people/{target.id}/delete/preview/",
                {},
                format="json",
                **_hdr(org.slug),
            )
        assert preview.status_code == 200, preview.content
        assert preview.json()["ok"] is True

        with organization_context(org):
            applied = api.post(
                f"/api/v1/admin/people/{target.id}/delete/",
                {"reason": "Duplicate import row"},
                format="json",
                **_hdr(org.slug),
            )
        assert applied.status_code == 200, applied.content
        assert not Person.all_objects.filter(pk=target.id).exists()
        assert AuditEvent.all_objects.filter(content_type="person_delete").exists()

    def test_delete_blocked_without_confirm_destructive(
        self, api, org, program, admin_user,
    ):
        target = Person.all_objects.create(
            organization=org, first_name="Cam", last_name="Per",
        )
        author = Person.all_objects.create(
            organization=org, first_name="Auth", last_name="Or",
        )
        template = ReflectionTemplate.all_objects.create(
            organization=org,
            name="Delete Org Daily",
            slug="daily",
            cadence="daily",
            schema={"fields": []},
        )
        Reflection.all_objects.create(
            organization=org,
            program=program,
            subject=target,
            author=author,
            template=template,
            period_start=date(2026, 7, 1),
            period_end=date(2026, 7, 7),
            answers={},
        )

        api.force_authenticate(user=admin_user)
        with organization_context(org):
            blocked = api.post(
                f"/api/v1/admin/people/{target.id}/delete/",
                {"reason": "Remove duplicate camper row"},
                format="json",
                **_hdr(org.slug),
            )
        assert blocked.status_code == 409

        with organization_context(org):
            applied = api.post(
                f"/api/v1/admin/people/{target.id}/delete/",
                {"reason": "Remove duplicate camper row", "confirm_destructive": True},
                format="json",
                **_hdr(org.slug),
            )
        assert applied.status_code == 200, applied.content
        assert not Person.all_objects.filter(pk=target.id).exists()
