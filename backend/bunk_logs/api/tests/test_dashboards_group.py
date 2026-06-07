"""Tests for ``GET /api/v1/dashboards/group/<group_id>/`` (unified group dashboard).

Covers the access resolver's role precedence (admin > leadership_team
> unit_head > camper_care > counselor > classroom_author), per-type
dispatch (bunk / unit / division / classroom), unsupported-type 400,
cross-org isolation, and the legacy ``/dashboards/bunks/<id>/`` alias.
"""
from __future__ import annotations

from datetime import date
from datetime import datetime
from datetime import time
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
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import Supervision
from bunk_logs.core.models import TemplateAssignment
from bunk_logs.core.time_utils import get_org_timezone
from bunk_logs.core.time_utils import get_today
from bunk_logs.notes.models import Observation
from bunk_logs.notes.models import ObservationSubject

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
def division(org, program):
    return AssignmentGroup.all_objects.create(
        organization=org, program=program,
        name="Division Aleph", slug="division-aleph",
        group_type="division", is_active=True,
    )


@pytest.fixture
def unit(org, program, division):
    return AssignmentGroup.all_objects.create(
        organization=org, program=program,
        name="Unit Alef", slug="unit-alef",
        group_type="unit", parent=division, is_active=True,
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


@pytest.fixture
def classroom(org, program):
    return AssignmentGroup.all_objects.create(
        organization=org, program=program,
        name="Hebrew 101", slug="hebrew-101",
        group_type="classroom", is_active=True,
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
    return f"/api/v1/dashboards/group/{bunk.id}/"


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
        _person, user = _make_person(org, first="No", last="Org", email="noorg@dash.test")
        api.force_authenticate(user=user)
        resp = api.get(url)
        assert resp.status_code == 403

    def test_authenticated_user_without_person_or_role_denied(self, api, org, url):
        _, user = _make_person(org, first="Lone", last="Wolf", email="lone@dash.test")
        api.force_authenticate(user=user)
        with organization_context(org):
            resp = api.get(url, **_hdr(org.slug))
        assert resp.status_code == 403

    def test_group_not_found_returns_generic_403(self, api, org, program):
        # Person has admin role but the group doesn't exist; expect 403
        # (not 404) so we don't leak existence to non-org callers.
        person, user = _make_person(org, first="Aaron", last="Admin", email="admin@dash.test")
        Membership.all_objects.create(
            program=program, person=person, role="admin", is_active=True,
        )
        api.force_authenticate(user=user)
        with organization_context(org):
            resp = api.get("/api/v1/dashboards/group/999999/", **_hdr(org.slug))
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Per-role happy paths against a BUNK group (no behavioral change from PR #134;
# kept so the unified URL keeps the same payload shape)
# ---------------------------------------------------------------------------


class TestBunkAccess:
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
        assert body["role_context"]["group_type"] == "bunk"
        assert body["role_context"]["can_edit"] is False
        # Bunk payload retains the existing header.bunk shape.
        assert body["header"]["bunk"]["id"] == bunk.id
        assert body["header"]["program_name"] == program.name

    def test_payload_includes_member_roster_with_roles(
        self, api, org, program, bunk, url,
    ):
        """The group payload lists authors + subjects with their program role,
        authors first."""
        admin_person, admin_user = _make_person(
            org, first="Aaron", last="Admin", email="roster-admin@dash.test",
        )
        Membership.all_objects.create(
            program=program, person=admin_person, role="admin", is_active=True,
        )
        counselor_person, _ = _make_person(
            org, first="Mira", last="Sandberg", email="roster-counselor@dash.test",
        )
        Membership.all_objects.create(
            program=program, person=counselor_person, role="counselor", is_active=True,
        )
        AssignmentGroupMembership.all_objects.create(
            group=bunk, person=counselor_person, role_in_group="author", is_active=True,
        )
        camper_person = Person.all_objects.create(
            organization=org, first_name="Alex", last_name="Camper",
        )
        Membership.all_objects.create(
            program=program, person=camper_person, role="camper", is_active=True,
        )
        AssignmentGroupMembership.all_objects.create(
            group=bunk, person=camper_person, role_in_group="subject", is_active=True,
        )
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            resp = api.get(url, **_hdr(org.slug))
        assert resp.status_code == 200, resp.content
        roster = resp.json()["roster"]
        assert [m["role_in_group"] for m in roster] == ["author", "subject"]
        by_id = {m["person_id"]: m for m in roster}
        assert by_id[counselor_person.id]["membership_role"] == "counselor"
        assert by_id[counselor_person.id]["name"] == "Mira Sandberg"
        assert by_id[camper_person.id]["membership_role"] == "camper"

    def test_bunk_dashboard_observations_bucketed_by_observed_at_date(
        self, api, org, program, bunk, url,
    ):
        admin_person, admin_user = _make_person(
            org, first="Aaron", last="Admin", email="obs-admin@dash.test",
        )
        Membership.all_objects.create(
            program=program, person=admin_person, role="admin", is_active=True,
        )
        author_person, _ = _make_person(
            org, first="Sam", last="Spec", email="spec@dash.test",
        )
        Membership.all_objects.create(
            program=program, person=author_person, role="specialist", is_active=True,
        )
        camper_person = Person.all_objects.create(
            organization=org, first_name="Pat", last_name="Camper",
        )
        Membership.all_objects.create(
            program=program, person=camper_person, role="camper", is_active=True,
        )
        AssignmentGroupMembership.all_objects.create(
            group=bunk, person=camper_person, role_in_group="subject", is_active=True,
        )

        today = get_today(org)
        yesterday = today - timedelta(days=1)
        tz = get_org_timezone(org)
        today_noon = datetime.combine(today, time(12, 0), tzinfo=tz)
        yesterday_noon = datetime.combine(yesterday, time(12, 0), tzinfo=tz)

        obs_today = Observation.all_objects.create(
            organization=org,
            program=program,
            author=author_person,
            author_role_at_write="specialist",
            body="Swim today",
            observed_at=today_noon,
        )
        ObservationSubject.objects.create(observation=obs_today, subject=camper_person)
        obs_yesterday = Observation.all_objects.create(
            organization=org,
            program=program,
            author=author_person,
            author_role_at_write="specialist",
            body="Swim yesterday",
            observed_at=yesterday_noon,
        )
        ObservationSubject.objects.create(observation=obs_yesterday, subject=camper_person)

        api.force_authenticate(user=admin_user)
        with organization_context(org):
            today_resp = api.get(f"{url}?date={today.isoformat()}", **_hdr(org.slug))
            yest_resp = api.get(f"{url}?date={yesterday.isoformat()}", **_hdr(org.slug))
        assert today_resp.status_code == 200, today_resp.content
        assert yest_resp.status_code == 200, yest_resp.content
        today_ids = {o["id"] for o in today_resp.json().get("observations", [])}
        yest_ids = {o["id"] for o in yest_resp.json().get("observations", [])}
        assert obs_today.id in today_ids
        assert obs_yesterday.id not in today_ids
        assert obs_yesterday.id in yest_ids
        assert obs_today.id not in yest_ids

    def test_counselor_without_authorship_denied(
        self, api, org, program, bunk, url,
    ):
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

    def test_leadership_team_has_org_wide_access(
        self, api, org, program, bunk, url,
    ):
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

    def test_legacy_bunks_alias_still_works(self, api, org, program, bunk):
        # /dashboards/bunks/<id>/ aliases the same view so callers
        # that migrated to PR #134 don't break.
        person, user = _make_person(
            org, first="Adi", last="Alias", email="alias@dash.test",
        )
        Membership.all_objects.create(
            program=program, person=person, role="admin", is_active=True,
        )
        api.force_authenticate(user=user)
        with organization_context(org):
            resp = api.get(
                f"/api/v1/dashboards/bunks/{bunk.id}/", **_hdr(org.slug),
            )
        assert resp.status_code == 200
        assert resp.json()["role_context"]["group_type"] == "bunk"


# ---------------------------------------------------------------------------
# UNIT group access + payload shape
# ---------------------------------------------------------------------------


class TestUnitAccess:
    @pytest.fixture
    def unit_url(self, unit):
        return f"/api/v1/dashboards/group/{unit.id}/"

    def test_admin_can_view(self, api, org, program, unit, unit_url):
        person, user = _make_person(
            org, first="Adi", last="Admin", email="adi-u@dash.test",
        )
        Membership.all_objects.create(
            program=program, person=person, role="admin", is_active=True,
        )
        api.force_authenticate(user=user)
        with organization_context(org):
            resp = api.get(unit_url, **_hdr(org.slug))
        assert resp.status_code == 200, resp.content
        body = resp.json()
        assert body["role_context"]["role"] == "admin"
        assert body["role_context"]["group_type"] == "unit"
        assert body["header"]["group"]["id"] == unit.id
        assert body["header"]["group"]["group_type"] == "unit"

    def test_lt_can_view(self, api, org, program, unit, unit_url):
        person, user = _make_person(
            org, first="LT", last="Unit", email="lt-u@dash.test",
        )
        Membership.all_objects.create(
            program=program, person=person, role="leadership_team", is_active=True,
        )
        api.force_authenticate(user=user)
        with organization_context(org):
            resp = api.get(unit_url, **_hdr(org.slug))
        assert resp.status_code == 200, resp.content
        assert resp.json()["role_context"]["role"] == "leadership_team"

    def test_unit_head_supervising_a_child_bunk_can_view(
        self, api, org, program, bunk, unit, unit_url,
    ):
        co_person, _ = _make_person(
            org, first="Coun", last="Sel", email="cs-u@dash.test",
        )
        co_membership = Membership.all_objects.create(
            program=program, person=co_person, role="counselor", is_active=True,
        )
        AssignmentGroupMembership.all_objects.create(
            group=bunk, person=co_person, role_in_group="author", is_active=True,
        )
        uh_person, uh_user = _make_person(
            org, first="Uni", last="Head", email="uh-u@dash.test",
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
            resp = api.get(unit_url, **_hdr(org.slug))
        assert resp.status_code == 200, resp.content
        assert resp.json()["role_context"]["role"] == "unit_head"

    def test_cc_caseload_includes_a_bunk_in_unit(
        self, api, org, program, bunk, unit, unit_url,
    ):
        cc_person, cc_user = _make_person(
            org, first="CC", last="Unit", email="cc-u@dash.test",
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
            resp = api.get(unit_url, **_hdr(org.slug))
        assert resp.status_code == 200, resp.content
        assert resp.json()["role_context"]["role"] == "camper_care"

    def test_counselor_authoring_a_child_bunk_denied(
        self, api, org, program, bunk, unit_url,
    ):
        # Counselors don't get rollup access at the unit level.
        person, user = _make_person(
            org, first="Just", last="Counselor", email="jc-u@dash.test",
        )
        Membership.all_objects.create(
            program=program, person=person, role="counselor", is_active=True,
        )
        AssignmentGroupMembership.all_objects.create(
            group=bunk, person=person, role_in_group="author", is_active=True,
        )
        api.force_authenticate(user=user)
        with organization_context(org):
            resp = api.get(unit_url, **_hdr(org.slug))
        assert resp.status_code == 403

    def test_unit_payload_lists_child_bunks(
        self, api, org, program, bunk, other_bunk, unit, unit_url,
    ):
        person, user = _make_person(
            org, first="Adi", last="A", email="adi-rows@dash.test",
        )
        Membership.all_objects.create(
            program=program, person=person, role="admin", is_active=True,
        )
        api.force_authenticate(user=user)
        with organization_context(org):
            resp = api.get(unit_url, **_hdr(org.slug))
        assert resp.status_code == 200
        body = resp.json()
        bunk_ids = {b["id"] for b in body["bunks"]}
        assert bunk_ids == {bunk.id, other_bunk.id}
        assert body["summary"]["bunk_count"] == 2


# ---------------------------------------------------------------------------
# DIVISION group access + payload shape
# ---------------------------------------------------------------------------


class TestDivisionAccess:
    @pytest.fixture
    def div_url(self, division):
        return f"/api/v1/dashboards/group/{division.id}/"

    def test_admin_can_view(self, api, org, program, division, unit, div_url):
        person, user = _make_person(
            org, first="Adi", last="Div", email="adi-d@dash.test",
        )
        Membership.all_objects.create(
            program=program, person=person, role="admin", is_active=True,
        )
        api.force_authenticate(user=user)
        with organization_context(org):
            resp = api.get(div_url, **_hdr(org.slug))
        assert resp.status_code == 200, resp.content
        body = resp.json()
        assert body["role_context"]["group_type"] == "division"
        assert body["header"]["group"]["id"] == division.id
        # Division payload exposes units array, not bunks.
        assert "units" in body
        unit_ids = {u["id"] for u in body["units"]}
        assert unit.id in unit_ids
        assert body["summary"]["unit_count"] >= 1

    def test_uh_supervising_descendant_bunk_can_view(
        self, api, org, program, bunk, div_url,
    ):
        co_person, _ = _make_person(
            org, first="Co", last="UnselDiv", email="co-d@dash.test",
        )
        co_membership = Membership.all_objects.create(
            program=program, person=co_person, role="counselor", is_active=True,
        )
        AssignmentGroupMembership.all_objects.create(
            group=bunk, person=co_person, role_in_group="author", is_active=True,
        )
        uh_person, uh_user = _make_person(
            org, first="Uni", last="Div", email="uh-d@dash.test",
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
            resp = api.get(div_url, **_hdr(org.slug))
        assert resp.status_code == 200, resp.content
        assert resp.json()["role_context"]["role"] == "unit_head"

    def test_counselor_denied(
        self, api, org, program, bunk, div_url,
    ):
        person, user = _make_person(
            org, first="Co", last="Div", email="co-cdiv@dash.test",
        )
        Membership.all_objects.create(
            program=program, person=person, role="counselor", is_active=True,
        )
        AssignmentGroupMembership.all_objects.create(
            group=bunk, person=person, role_in_group="author", is_active=True,
        )
        api.force_authenticate(user=user)
        with organization_context(org):
            resp = api.get(div_url, **_hdr(org.slug))
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# CLASSROOM group access + payload shape
# ---------------------------------------------------------------------------


class TestClassroomAccess:
    @pytest.fixture
    def class_url(self, classroom):
        return f"/api/v1/dashboards/group/{classroom.id}/"

    def test_faculty_author_can_view(
        self, api, org, program, classroom, class_url,
    ):
        person, user = _make_person(
            org, first="Fac", last="Ulty", email="fac@dash.test",
        )
        Membership.all_objects.create(
            program=program, person=person, role="faculty", is_active=True,
        )
        AssignmentGroupMembership.all_objects.create(
            group=classroom, person=person,
            role_in_group="author", is_active=True,
        )
        api.force_authenticate(user=user)
        with organization_context(org):
            resp = api.get(class_url, **_hdr(org.slug))
        assert resp.status_code == 200, resp.content
        body = resp.json()
        assert body["role_context"]["role"] == "classroom_author"
        assert body["role_context"]["group_type"] == "classroom"
        assert body["header"]["group"]["id"] == classroom.id
        assert "subjects" in body
        assert "authors" in body

    def test_madrich_author_can_view(
        self, api, org, program, classroom, class_url,
    ):
        person, user = _make_person(
            org, first="Mad", last="Rich", email="mad@dash.test",
        )
        Membership.all_objects.create(
            program=program, person=person, role="madrich", is_active=True,
        )
        AssignmentGroupMembership.all_objects.create(
            group=classroom, person=person,
            role_in_group="author", is_active=True,
        )
        api.force_authenticate(user=user)
        with organization_context(org):
            resp = api.get(class_url, **_hdr(org.slug))
        assert resp.status_code == 200, resp.content
        assert resp.json()["role_context"]["role"] == "classroom_author"

    def test_non_author_faculty_denied(
        self, api, org, program, class_url,
    ):
        # Faculty Membership in the program but no AGM(author) on the classroom.
        person, user = _make_person(
            org, first="No", last="Auth", email="noauth@dash.test",
        )
        Membership.all_objects.create(
            program=program, person=person, role="faculty", is_active=True,
        )
        api.force_authenticate(user=user)
        with organization_context(org):
            resp = api.get(class_url, **_hdr(org.slug))
        assert resp.status_code == 403

    def test_counselor_with_authorship_still_denied(
        self, api, org, program, classroom, class_url,
    ):
        # Counselor role doesn't grant classroom access even with AGM(author).
        person, user = _make_person(
            org, first="Coun", last="Class", email="coun-cl@dash.test",
        )
        Membership.all_objects.create(
            program=program, person=person, role="counselor", is_active=True,
        )
        AssignmentGroupMembership.all_objects.create(
            group=classroom, person=person,
            role_in_group="author", is_active=True,
        )
        api.force_authenticate(user=user)
        with organization_context(org):
            resp = api.get(class_url, **_hdr(org.slug))
        assert resp.status_code == 403

    def test_admin_can_view(
        self, api, org, program, classroom, class_url,
    ):
        person, user = _make_person(
            org, first="Adi", last="Class", email="adi-cl@dash.test",
        )
        Membership.all_objects.create(
            program=program, person=person, role="admin", is_active=True,
        )
        api.force_authenticate(user=user)
        with organization_context(org):
            resp = api.get(class_url, **_hdr(org.slug))
        assert resp.status_code == 200, resp.content
        assert resp.json()["role_context"]["role"] == "admin"


# ---------------------------------------------------------------------------
# Unsupported group_type
# ---------------------------------------------------------------------------


class TestUnsupportedGroupType:
    def test_cohort_returns_400(self, api, org, program):
        cohort = AssignmentGroup.all_objects.create(
            organization=org, program=program,
            name="Cohort A", slug="cohort-a",
            group_type="cohort", is_active=True,
        )
        person, user = _make_person(
            org, first="Adi", last="Coh", email="adi-coh@dash.test",
        )
        Membership.all_objects.create(
            program=program, person=person, role="admin", is_active=True,
        )
        api.force_authenticate(user=user)
        with organization_context(org):
            resp = api.get(
                f"/api/v1/dashboards/group/{cohort.id}/", **_hdr(org.slug),
            )
        assert resp.status_code == 400
        # Message should name the unsupported group_type so the
        # frontend can render an actionable empty-state.
        assert "cohort" in str(resp.json()).lower()


# ---------------------------------------------------------------------------
# Precedence + cross-org isolation
# ---------------------------------------------------------------------------


class TestPrecedenceAndIsolation:
    def test_admin_takes_precedence_over_counselor(
        self, api, org, program, bunk, url,
    ):
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
        # Person + admin Membership in org A; group lives in org B.
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
            resp = api.get(
                f"/api/v1/dashboards/group/{bunk_b.id}/", **_hdr(org_b.slug),
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


class TestAssignedTemplateCards:
    """The unified payload exposes a ``templates`` array of per-template
    response cards for templates assigned to the group (target_type=
    'assignment_group') whose date window contains the selected date."""

    def _template(self, org):
        return ReflectionTemplate.all_objects.create(
            organization=org, name="Bunk Pulse", slug="grp-bunk-pulse",
            cadence="daily", subject_mode="single_subject",
            assignment_scope="per_subject_in_group",
            assignment_group_types=["bunk"],
            author_role_filter=["counselor"], subject_role_filter=["camper"],
            schema={
                "fields": [
                    {
                        "key": "overall", "type": "single_rating",
                        "scale": [1, 5], "required": True,
                    },
                ],
            },
        )

    def _admin(self, api, org, program, email):
        person, user = _make_person(org, first="Adi", last="Tpl", email=email)
        Membership.all_objects.create(
            program=program, person=person, role="admin", is_active=True,
        )
        api.force_authenticate(user=user)
        return person

    def test_assigned_template_card_with_reflection(
        self, api, org, program, bunk, url,
    ):
        self._admin(api, org, program, "adi-tpl1@dash.test")
        tpl = self._template(org)
        today = get_today(org)
        TemplateAssignment.all_objects.create(
            organization=org, program=program, template=tpl,
            target_type=TemplateAssignment.TargetType.ASSIGNMENT_GROUP,
            assignment_group=bunk, start_date=today - timedelta(days=3),
            end_date=None, status=TemplateAssignment.Status.ACTIVE,
        )
        camper = _make_person(org, first="Cam", last="Per", email="cam-tpl@dash.test")[0]
        Reflection.all_objects.create(
            organization=org, program=program, template=tpl,
            subject=camper, assignment_group=bunk,
            period_start=today, period_end=today,
            answers={"overall": 5}, language="en", is_complete=True,
        )
        with organization_context(org):
            resp = api.get(url, **_hdr(org.slug))
        assert resp.status_code == 200, resp.content
        cards = resp.json()["templates"]
        assert len(cards) == 1
        card = cards[0]
        assert card["template"]["id"] == tpl.id
        assert card["summary"]["total_reflections"] == 1
        assert card["reflections"][0]["subject"]["id"] == camper.id
        assert any(s["label"] == "overall" for s in card["rating_series"])

    def test_assignment_shown_even_with_zero_reflections(
        self, api, org, program, bunk, url,
    ):
        self._admin(api, org, program, "adi-tpl2@dash.test")
        tpl = self._template(org)
        today = get_today(org)
        TemplateAssignment.all_objects.create(
            organization=org, program=program, template=tpl,
            target_type=TemplateAssignment.TargetType.ASSIGNMENT_GROUP,
            assignment_group=bunk, start_date=today, end_date=None,
            status=TemplateAssignment.Status.ACTIVE,
        )
        with organization_context(org):
            resp = api.get(url, **_hdr(org.slug))
        cards = resp.json()["templates"]
        assert len(cards) == 1
        assert cards[0]["summary"]["total_reflections"] == 0

    def test_assignment_outside_date_window_excluded(
        self, api, org, program, bunk, url,
    ):
        self._admin(api, org, program, "adi-tpl3@dash.test")
        tpl = self._template(org)
        today = get_today(org)
        TemplateAssignment.all_objects.create(
            organization=org, program=program, template=tpl,
            target_type=TemplateAssignment.TargetType.ASSIGNMENT_GROUP,
            assignment_group=bunk,
            start_date=today - timedelta(days=10),
            end_date=today - timedelta(days=5),
            status=TemplateAssignment.Status.ENDED,
        )
        with organization_context(org):
            resp = api.get(url, **_hdr(org.slug))
        assert resp.json()["templates"] == []

    def test_group_without_assignments_has_empty_templates(
        self, api, org, program, bunk, url,
    ):
        self._admin(api, org, program, "adi-tpl4@dash.test")
        with organization_context(org):
            resp = api.get(url, **_hdr(org.slug))
        assert resp.status_code == 200
        assert resp.json()["templates"] == []


class TestDateHandling:
    def test_future_date_clamped_to_today(self, api, org, program, bunk, url):
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
        assert resp.status_code == 200
        body = resp.json()
        assert body["header"]["date"] == body["header"]["today"]

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
