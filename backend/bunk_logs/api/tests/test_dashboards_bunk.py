"""Tests for ``GET /api/v1/dashboards/bunks/<bunk_id>/`` (unified bunk dashboard).

Covers the access resolver's role precedence (admin > leadership_team
> unit_head > camper_care > counselor), the org/program scoping, and
the universal-URL guarantees we expose to the frontend (consistent
payload shape across roles, no bunk-existence leaks across orgs).
"""
from __future__ import annotations

from datetime import date
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Supervision

User = get_user_model()
pytestmark = pytest.mark.django_db


def _hdr(slug: str) -> dict:
    return {"HTTP_X_ORGANIZATION_SLUG": slug}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def org():
    return Organization.objects.create(name="Dash Camp", slug="dash-camp")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="Dash Camp Summer",
        slug="dash-summer",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def unit(org, program):
    return AssignmentGroup.all_objects.create(
        organization=org, program=program,
        name="Unit Alef", slug="unit-alef",
        group_type="unit", is_active=True,
    )


@pytest.fixture
def bunk(org, program, unit):
    return AssignmentGroup.all_objects.create(
        organization=org, program=program,
        name="Bunk Birch", slug="bunk-birch",
        group_type="bunk", parent=unit, is_active=True,
    )


@pytest.fixture
def other_bunk(org, program, unit):
    return AssignmentGroup.all_objects.create(
        organization=org, program=program,
        name="Bunk Pine", slug="bunk-pine",
        group_type="bunk", parent=unit, is_active=True,
    )


def _make_person(org, *, first, last, email):
    user = User.objects.create_user(email=email, password="pw")
    person = Person.all_objects.create(
        organization=org, first_name=first, last_name=last, user=user,
    )
    return person, user


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def url(bunk):
    return f"/api/v1/dashboards/bunks/{bunk.id}/"


# ---------------------------------------------------------------------------
# Authentication + Person-profile prelude
# ---------------------------------------------------------------------------


class TestPrelude:
    def test_unauthenticated_rejected(self, api, org, url):
        with organization_context(org):
            resp = api.get(url, **_hdr(org.slug))
        assert resp.status_code in (401, 403)

    def test_missing_organization_context_rejected(self, api, org, url):
        # No X-Organization-Slug header — middleware leaves request.organization unset.
        person, user = _make_person(org, first="No", last="Org", email="noorg@dash.test")
        api.force_authenticate(user=user)
        resp = api.get(url)
        assert resp.status_code == 403

    def test_authenticated_user_without_person_or_role_denied(self, api, org, url):
        _, user = _make_person(org, first="Lone", last="Wolf", email="lone@dash.test")
        api.force_authenticate(user=user)
        with organization_context(org):
            resp = api.get(url, **_hdr(org.slug))
        assert resp.status_code == 403

    def test_bunk_not_found_returns_generic_403(self, api, org, program):
        # Person has admin role but the bunk doesn't exist; expect 403
        # (not 404) so we don't leak existence to non-org callers.
        person, user = _make_person(org, first="Aaron", last="Admin", email="admin@dash.test")
        Membership.all_objects.create(
            program=program, person=person, role="admin", is_active=True,
        )
        api.force_authenticate(user=user)
        with organization_context(org):
            resp = api.get("/api/v1/dashboards/bunks/999999/", **_hdr(org.slug))
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Per-role happy paths + role_context
# ---------------------------------------------------------------------------


class TestRoleAccess:
    def test_counselor_authoring_bunk_can_view(
        self, api, org, program, bunk, url,
    ):
        person, user = _make_person(
            org, first="Mira", last="Sandberg", email="counselor@dash.test",
        )
        Membership.all_objects.create(
            program=program, person=person, role="counselor", is_active=True,
        )
        AssignmentGroupMembership.all_objects.create(
            group=bunk, person=person, role_in_group="author", is_active=True,
        )
        api.force_authenticate(user=user)
        with organization_context(org):
            resp = api.get(url, **_hdr(org.slug))
        assert resp.status_code == 200, resp.content
        body = resp.json()
        assert body["role_context"]["role"] == "counselor"
        assert body["role_context"]["can_edit"] is False
        assert body["header"]["bunk"]["id"] == bunk.id

    def test_counselor_without_authorship_denied(
        self, api, org, program, bunk, url,
    ):
        # Counselor Membership alone is not enough — needs AGM(author).
        person, user = _make_person(
            org, first="Bara", last="Lev", email="bara@dash.test",
        )
        Membership.all_objects.create(
            program=program, person=person, role="counselor", is_active=True,
        )
        api.force_authenticate(user=user)
        with organization_context(org):
            resp = api.get(url, **_hdr(org.slug))
        assert resp.status_code == 403

    def test_unit_head_supervising_bunk_can_view(
        self, api, org, program, bunk, url,
    ):
        # UH supervises a counselor who authors the bunk.
        co_person, _ = _make_person(
            org, first="Counsey", last="Lou", email="counsey@dash.test",
        )
        co_membership = Membership.all_objects.create(
            program=program, person=co_person, role="counselor", is_active=True,
        )
        AssignmentGroupMembership.all_objects.create(
            group=bunk, person=co_person, role_in_group="author", is_active=True,
        )
        uh_person, uh_user = _make_person(
            org, first="Avery", last="Reeves", email="uh@dash.test",
        )
        uh_membership = Membership.all_objects.create(
            program=program, person=uh_person, role="unit_head", is_active=True,
        )
        Supervision.all_objects.create(
            supervisor_membership=uh_membership,
            target_type="membership",
            target_membership=co_membership,
            start_date=date(2026, 1, 1),
        )
        api.force_authenticate(user=uh_user)
        with organization_context(org):
            resp = api.get(url, **_hdr(org.slug))
        assert resp.status_code == 200, resp.content
        assert resp.json()["role_context"]["role"] == "unit_head"

    def test_unit_head_not_supervising_bunk_denied(
        self, api, org, program, bunk, other_bunk, url,
    ):
        # UH supervises a counselor on *other_bunk* but the requested
        # URL is `bunk`. Expect 403 even though they have the role.
        co_person, _ = _make_person(
            org, first="Casey", last="K", email="casey@dash.test",
        )
        co_membership = Membership.all_objects.create(
            program=program, person=co_person, role="counselor", is_active=True,
        )
        AssignmentGroupMembership.all_objects.create(
            group=other_bunk, person=co_person, role_in_group="author", is_active=True,
        )
        uh_person, uh_user = _make_person(
            org, first="Una", last="Head", email="unsup@dash.test",
        )
        uh_membership = Membership.all_objects.create(
            program=program, person=uh_person, role="unit_head", is_active=True,
        )
        Supervision.all_objects.create(
            supervisor_membership=uh_membership,
            target_type="membership",
            target_membership=co_membership,
            start_date=date(2026, 1, 1),
        )
        api.force_authenticate(user=uh_user)
        with organization_context(org):
            resp = api.get(url, **_hdr(org.slug))
        assert resp.status_code == 403

    def test_camper_care_with_bunk_on_caseload_can_view(
        self, api, org, program, bunk, url,
    ):
        cc_person, cc_user = _make_person(
            org, first="Pat", last="Coster", email="cc@dash.test",
        )
        cc_membership = Membership.all_objects.create(
            program=program, person=cc_person, role="camper_care", is_active=True,
        )
        Supervision.all_objects.create(
            supervisor_membership=cc_membership,
            target_type="bunk",
            target_bunk=bunk,
            start_date=date(2026, 1, 1),
        )
        api.force_authenticate(user=cc_user)
        with organization_context(org):
            resp = api.get(url, **_hdr(org.slug))
        assert resp.status_code == 200, resp.content
        assert resp.json()["role_context"]["role"] == "camper_care"

    def test_camper_care_off_caseload_denied(
        self, api, org, program, bunk, other_bunk, url,
    ):
        cc_person, cc_user = _make_person(
            org, first="Off", last="Caseload", email="cc-off@dash.test",
        )
        cc_membership = Membership.all_objects.create(
            program=program, person=cc_person, role="camper_care", is_active=True,
        )
        # Caseload covers other_bunk only.
        Supervision.all_objects.create(
            supervisor_membership=cc_membership,
            target_type="bunk",
            target_bunk=other_bunk,
            start_date=date(2026, 1, 1),
        )
        api.force_authenticate(user=cc_user)
        with organization_context(org):
            resp = api.get(url, **_hdr(org.slug))
        assert resp.status_code == 403

    def test_leadership_team_has_org_wide_access(
        self, api, org, program, bunk, url,
    ):
        # LT has no direct Supervision rows to the bunk yet still sees it.
        lt_person, lt_user = _make_person(
            org, first="Lara", last="Lead", email="lt@dash.test",
        )
        Membership.all_objects.create(
            program=program, person=lt_person, role="leadership_team", is_active=True,
        )
        api.force_authenticate(user=lt_user)
        with organization_context(org):
            resp = api.get(url, **_hdr(org.slug))
        assert resp.status_code == 200, resp.content
        assert resp.json()["role_context"]["role"] == "leadership_team"

    def test_admin_membership_has_org_wide_access(
        self, api, org, program, bunk, url,
    ):
        admin_person, admin_user = _make_person(
            org, first="Adi", last="Admin", email="adi@dash.test",
        )
        Membership.all_objects.create(
            program=program, person=admin_person, role="admin", is_active=True,
        )
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            resp = api.get(url, **_hdr(org.slug))
        assert resp.status_code == 200, resp.content
        assert resp.json()["role_context"]["role"] == "admin"

    def test_superuser_without_person_resolves_as_admin(
        self, api, org, bunk, url,
    ):
        user = User.objects.create_superuser(email="su@dash.test", password="pw")
        api.force_authenticate(user=user)
        with organization_context(org):
            resp = api.get(url, **_hdr(org.slug))
        assert resp.status_code == 200, resp.content
        assert resp.json()["role_context"]["role"] == "admin"


# ---------------------------------------------------------------------------
# Precedence + cross-org isolation
# ---------------------------------------------------------------------------


class TestPrecedenceAndIsolation:
    def test_admin_takes_precedence_over_counselor(
        self, api, org, program, bunk, url,
    ):
        # User holds BOTH admin and counselor Memberships; resolver
        # must report admin (the higher-precedence role).
        person, user = _make_person(
            org, first="Multi", last="Hat", email="multi@dash.test",
        )
        Membership.all_objects.create(
            program=program, person=person, role="counselor", is_active=True,
        )
        Membership.all_objects.create(
            program=program, person=person, role="admin", is_active=True,
        )
        AssignmentGroupMembership.all_objects.create(
            group=bunk, person=person, role_in_group="author", is_active=True,
        )
        api.force_authenticate(user=user)
        with organization_context(org):
            resp = api.get(url, **_hdr(org.slug))
        assert resp.status_code == 200
        assert resp.json()["role_context"]["role"] == "admin"

    def test_cross_org_membership_does_not_grant_access(self, api):
        # Person + admin Membership in org A; bunk lives in org B.
        # Request goes through org B's slug. Expect generic 403 (no
        # bunk-existence leak).
        org_a = Organization.objects.create(name="Org A", slug="org-a")
        org_b = Organization.objects.create(name="Org B", slug="org-b")
        program_b = Program.all_objects.create(
            organization=org_b, name="Org B Summer", slug="b-summer",
            program_type="summer_camp",
            start_date=date(2026, 6, 1), end_date=date(2026, 8, 31),
        )
        bunk_b = AssignmentGroup.all_objects.create(
            organization=org_b, program=program_b,
            name="B Bunk", slug="b-bunk", group_type="bunk", is_active=True,
        )

        program_a = Program.all_objects.create(
            organization=org_a, name="Org A Summer", slug="a-summer",
            program_type="summer_camp",
            start_date=date(2026, 6, 1), end_date=date(2026, 8, 31),
        )
        person_a, user_a = _make_person(
            org_a, first="X", last="Org", email="x@dash.test",
        )
        Membership.all_objects.create(
            program=program_a, person=person_a, role="admin", is_active=True,
        )
        api.force_authenticate(user=user_a)
        with organization_context(org_b):
            # Caller targets org B; Person belongs to org A. The
            # resolver should reject before the role lookup since the
            # bunk + org context point at a tenant the user is not in.
            resp = api.get(
                f"/api/v1/dashboards/bunks/{bunk_b.id}/", **_hdr(org_b.slug),
            )
        assert resp.status_code == 403

    def test_inactive_membership_does_not_grant_access(
        self, api, org, program, bunk, url,
    ):
        person, user = _make_person(
            org, first="Used", last="ToBe", email="exuh@dash.test",
        )
        Membership.all_objects.create(
            program=program, person=person, role="unit_head", is_active=False,
        )
        api.force_authenticate(user=user)
        with organization_context(org):
            resp = api.get(url, **_hdr(org.slug))
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Date handling
# ---------------------------------------------------------------------------


class TestDateHandling:
    def test_future_date_rejected(self, api, org, program, bunk, url):
        person, user = _make_person(
            org, first="LT", last="Future", email="ltf@dash.test",
        )
        Membership.all_objects.create(
            program=program, person=person, role="leadership_team", is_active=True,
        )
        future = (date.today() + timedelta(days=2)).isoformat()
        api.force_authenticate(user=user)
        with organization_context(org):
            resp = api.get(f"{url}?date={future}", **_hdr(org.slug))
        assert resp.status_code == 400

    def test_invalid_date_format_rejected(self, api, org, program, bunk, url):
        person, user = _make_person(
            org, first="Bad", last="Date", email="badd@dash.test",
        )
        Membership.all_objects.create(
            program=program, person=person, role="leadership_team", is_active=True,
        )
        api.force_authenticate(user=user)
        with organization_context(org):
            resp = api.get(f"{url}?date=not-a-date", **_hdr(org.slug))
        assert resp.status_code == 400
