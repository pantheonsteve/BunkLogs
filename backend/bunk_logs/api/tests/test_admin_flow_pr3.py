"""API tests for Step 7_13 PR3 -- search + templates oversight + bulk import.

Lean coverage: one happy path + one auth gate + one critical edge per
endpoint, plus org isolation for the most leak-prone surface (search).
"""

from __future__ import annotations

import io
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import AuditEvent
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import ReflectionTemplate

User = get_user_model()
pytestmark = pytest.mark.django_db


def _hdr(slug: str) -> dict:
    return {"HTTP_X_ORGANIZATION_SLUG": slug}


# ---------------------------------------------------------------------------
# Fixtures (shared with PR2 in pattern; intentionally local for isolation)
# ---------------------------------------------------------------------------


@pytest.fixture
def api() -> APIClient:
    return APIClient()


@pytest.fixture
def org():
    return Organization.objects.create(name="PR3 Org", slug="pr3-org")


@pytest.fixture
def other_org():
    return Organization.objects.create(name="PR3 Other", slug="pr3-other")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org, name="PR3 Org Summer", slug="pr3-summer",
        program_type="summer_camp",
        start_date=date(2026, 6, 1), end_date=date(2026, 8, 31),
    )


@pytest.fixture
def other_program(other_org):
    return Program.all_objects.create(
        organization=other_org, name="PR3 Other Summer", slug="pr3-other-summer",
        program_type="summer_camp",
        start_date=date(2026, 6, 1), end_date=date(2026, 8, 31),
    )


@pytest.fixture
def admin_user(org, program):
    u = User.objects.create_user(email="admin-pr3@example.com", password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="Ad", last_name="Min", user=u,
    )
    Membership.all_objects.create(
        program=program, person=person, role="admin", is_active=True,
    )
    return u


@pytest.fixture
def admin_membership(admin_user):
    person = Person.all_objects.get(user=admin_user)
    return Membership.all_objects.get(person=person, role="admin")


@pytest.fixture
def non_admin_user(org, program):
    u = User.objects.create_user(email="other-pr3@example.com", password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="Co", last_name="Un", user=u,
    )
    Membership.all_objects.create(
        program=program, person=person, role="counselor", is_active=True,
    )
    return u


# ---------------------------------------------------------------------------
# Global search
# ---------------------------------------------------------------------------


class TestAdminGlobalSearch:
    URL = "/api/v1/admin/search/"

    def test_short_query_rejected(self, api, org, admin_user):
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.get(f"{self.URL}?q=a", **_hdr(org.slug))
        assert r.status_code == 400

    def test_finds_people_in_org(
        self, api, org, program, admin_user,
    ):
        with organization_context(org):
            Person.all_objects.create(
                organization=org, first_name="Hermione",
                last_name="Granger", email="hg@example.com",
            )
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.get(f"{self.URL}?q=hermione", **_hdr(org.slug))
        assert r.status_code == 200, r.content
        body = r.json()
        assert any(
            row["label"].startswith("Hermione")
            for row in body["groups"]["people"]
        )

    def test_does_not_leak_cross_org(
        self, api, org, other_org, admin_user, other_program,
    ):
        # Persons in OTHER org with the same keyword must not show up in search.
        with organization_context(other_org):
            Person.all_objects.create(
                organization=other_org, first_name="Unique",
                last_name="OtherOrg", email="u@example.com",
            )
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.get(
                f"{self.URL}?q=UniqueKeywordForOtherOrg",
                **_hdr(org.slug),
            )
        assert r.status_code == 200
        body = r.json()
        for group in body["groups"].values():
            assert group == [] or all(
                "UniqueKeywordForOtherOrg" not in (row.get("secondary") or "")
                for row in group
            )

    def test_non_admin_blocked(self, api, org, non_admin_user):
        api.force_authenticate(user=non_admin_user)
        with organization_context(org):
            r = api.get(f"{self.URL}?q=anything", **_hdr(org.slug))
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Templates oversight
# ---------------------------------------------------------------------------


class TestAdminTemplates:
    URL = "/api/v1/admin/templates/"

    def test_pending_review_surfaces(self, api, org, admin_user):
        with organization_context(org):
            tpl = ReflectionTemplate.all_objects.create(
                organization=org, program_type="summer_camp",
                role="counselor", name="Recently Published",
                slug="recently-published", cadence="daily",
                schema={"fields": [{"key": "k", "label": "K", "type": "long_text", "prompts": {"en": "?"}}]},
                languages=["en"], subject_mode="self",
                status=ReflectionTemplate.Status.PUBLISHED,
                published_at=timezone.now(),
            )
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.get(self.URL, **_hdr(org.slug))
        assert r.status_code == 200
        body = r.json()
        assert body["pending_review_count"] >= 1
        target = next(t for t in body["results"] if t["id"] == tpl.id)
        assert target["pending_review"] is True

    def test_review_post_clears_pending(
        self, api, org, admin_user, admin_membership,
    ):
        with organization_context(org):
            tpl = ReflectionTemplate.all_objects.create(
                organization=org, program_type="summer_camp",
                role="counselor", name="Needs Review",
                slug="needs-review", cadence="daily",
                schema={"fields": [{"key": "k", "label": "K", "type": "long_text", "prompts": {"en": "?"}}]},
                languages=["en"], subject_mode="self",
                status=ReflectionTemplate.Status.PUBLISHED,
                published_at=timezone.now(),
            )
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.post(
                f"/api/v1/admin/templates/{tpl.id}/review/",
                {"review_status": "reviewed", "review_note": "LGTM"},
                format="json", **_hdr(org.slug),
            )
        assert r.status_code == 200
        body = r.json()
        assert body["review_status"] == "reviewed"
        assert body["pending_review"] is False
        # Audit event captured.
        assert AuditEvent.all_objects.filter(
            content_type="reflection_template",
            content_id=str(tpl.id),
        ).exists()

    def test_review_invalid_status_400(
        self, api, org, admin_user,
    ):
        with organization_context(org):
            tpl = ReflectionTemplate.all_objects.create(
                organization=org, program_type="summer_camp",
                role="counselor", name="X",
                slug="x-slug", cadence="daily",
                schema={"fields": [{"key": "k", "label": "K", "type": "long_text", "prompts": {"en": "?"}}]},
                languages=["en"], subject_mode="self",
            )
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.post(
                f"/api/v1/admin/templates/{tpl.id}/review/",
                {"review_status": "lgtm"},
                format="json", **_hdr(org.slug),
            )
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Bulk import preview
# ---------------------------------------------------------------------------


class TestAdminBulkImportPreview:
    URL = "/api/v1/admin/people/import/preview/"

    def _csv(self, rows: list[dict]) -> io.BytesIO:
        import csv as csv_mod
        buf = io.StringIO()
        writer = csv_mod.DictWriter(buf, fieldnames=[
            "campminder_id", "first_name", "last_name", "email", "role",
            "bunk_name", "unit_name", "division_name",
            "caseload_name", "caseload_owner_campminder_id",
            "language_preference", "tags",
        ])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        b = io.BytesIO(buf.getvalue().encode("utf-8"))
        b.name = "test.csv"
        return b

    def test_preview_classifies_rows(self, api, org, program, admin_user):
        # Seed an existing Person so we can verify "noop" classification.
        with organization_context(org):
            Person.all_objects.create(
                organization=org, first_name="Ex", last_name="Isting",
                email="ex@example.com",
                external_ids={"campminder_id": "EX1"},
            )
        api.force_authenticate(user=admin_user)
        csv_file = self._csv([
            # No external id -> skip
            {"first_name": "Nope", "last_name": "Boo"},
            # Unknown role -> skip
            {"campminder_id": "C1", "first_name": "Bad", "last_name": "Role", "role": "wizard"},
            # New person -> add
            {"campminder_id": "C2", "first_name": "Brand", "last_name": "New", "role": "counselor"},
            # Existing person, same data -> noop
            {"campminder_id": "EX1", "first_name": "Ex", "last_name": "Isting", "email": "ex@example.com", "role": "counselor"},
        ])
        with organization_context(org):
            r = api.post(self.URL, {
                "source": "campminder",
                "program_slug": program.slug,
                "csv": csv_file,
            }, format="multipart", **_hdr(org.slug))
        assert r.status_code == 200, r.content
        body = r.json()
        assert body["summary"]["row_count"] == 4
        assert body["summary"]["skip"] >= 2
        assert body["summary"]["add"] >= 1
        assert body["summary"]["noop"] >= 1

    def test_unknown_source_400(self, api, org, program, admin_user):
        api.force_authenticate(user=admin_user)
        csv_file = self._csv([])
        with organization_context(org):
            r = api.post(self.URL, {
                "source": "made_up",
                "program_slug": program.slug,
                "csv": csv_file,
            }, format="multipart", **_hdr(org.slug))
        assert r.status_code == 400

    def test_non_admin_blocked(self, api, org, program, non_admin_user):
        api.force_authenticate(user=non_admin_user)
        csv_file = self._csv([])
        with organization_context(org):
            r = api.post(self.URL, {
                "source": "campminder",
                "program_slug": program.slug,
                "csv": csv_file,
            }, format="multipart", **_hdr(org.slug))
        assert r.status_code == 403
