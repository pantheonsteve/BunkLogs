"""API tests for the Supervision admin endpoints (Step 7_3)."""

from __future__ import annotations

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Supervision
from bunk_logs.core.models import SupervisionEvent

User = get_user_model()
pytestmark = pytest.mark.django_db


def _hdr(slug: str) -> dict:
    return {"HTTP_X_ORGANIZATION_SLUG": slug}


@pytest.fixture
def api() -> APIClient:
    return APIClient()


@pytest.fixture
def org():
    return Organization.objects.create(name="API Sup Org", slug="api-sup-org")


@pytest.fixture
def other_org():
    return Organization.objects.create(name="API Sup Other", slug="api-sup-other")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="API Sup Org Summer",
        slug="api-sup-summer",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def other_program(other_org):
    return Program.all_objects.create(
        organization=other_org,
        name="API Sup Other Summer",
        slug="api-sup-other-summer",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def admin_user(org, program):
    u = User.objects.create_user(email="supadmin@example.com", password="pw")
    p = Person.all_objects.create(
        organization=org, first_name="Ad", last_name="Min", user=u,
    )
    Membership.all_objects.create(
        program=program, person=p, role="admin", is_active=True,
    )
    return u


@pytest.fixture
def uh_user(org, program):
    u = User.objects.create_user(email="uh@example.com", password="pw")
    p = Person.all_objects.create(
        organization=org, first_name="U", last_name="H", user=u,
    )
    Membership.all_objects.create(
        program=program, person=p, role="unit_head", is_active=True,
    )
    return u


@pytest.fixture
def uh_membership(org, program):
    p = Person.all_objects.create(organization=org, first_name="UHM", last_name="X")
    return Membership.all_objects.create(
        program=program, person=p, role="unit_head", is_active=True,
    )


@pytest.fixture
def counselor_membership(org, program):
    p = Person.all_objects.create(organization=org, first_name="CN", last_name="X")
    return Membership.all_objects.create(
        program=program, person=p, role="counselor", is_active=True,
    )


@pytest.fixture
def bunk(org, program):
    return AssignmentGroup.all_objects.create(
        organization=org,
        program=program,
        name="Bunk Twelve",
        slug="bunk-12",
        group_type="bunk",
    )


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------


class TestSupervisionAuthorization:
    def test_unauthenticated_cannot_list(self, api, org):
        with organization_context(org):
            r = api.get("/api/v1/supervisions/", **_hdr(org.slug))
        assert r.status_code in (401, 403)

    def test_uh_cannot_create_their_own_supervision(
        self, api, org, uh_user, uh_membership, counselor_membership,
    ):
        api.force_authenticate(user=uh_user)
        with organization_context(org):
            r = api.post(
                "/api/v1/supervisions/",
                {
                    "supervisor_membership": uh_membership.id,
                    "target_type": "membership",
                    "target_membership": counselor_membership.id,
                    "start_date": "2026-06-01",
                },
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 403

    def test_admin_can_create(
        self, api, org, admin_user, uh_membership, counselor_membership,
    ):
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.post(
                "/api/v1/supervisions/",
                {
                    "supervisor_membership": uh_membership.id,
                    "target_type": "membership",
                    "target_membership": counselor_membership.id,
                    "start_date": "2026-06-01",
                },
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 201, r.content
        assert Supervision.all_objects.filter(
            supervisor_membership=uh_membership,
            target_membership=counselor_membership,
        ).count() == 1


# ---------------------------------------------------------------------------
# List + filter
# ---------------------------------------------------------------------------


class TestSupervisionList:
    def test_list_filters_by_supervisor_membership_id(
        self, api, org, admin_user, uh_membership, counselor_membership, bunk,
    ):
        cc_person = Person.all_objects.create(
            organization=org, first_name="Cc", last_name="X",
        )
        cc = Membership.all_objects.create(
            program=uh_membership.program, person=cc_person,
            role="camper_care", is_active=True,
        )
        Supervision.all_objects.create(
            supervisor_membership=uh_membership,
            target_type="membership",
            target_membership=counselor_membership,
            start_date=date(2026, 6, 1),
        )
        Supervision.all_objects.create(
            supervisor_membership=cc,
            target_type="bunk",
            target_bunk=bunk,
            start_date=date(2026, 6, 1),
        )
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.get(
                "/api/v1/supervisions/",
                {"supervisor_membership_id": uh_membership.id},
                **_hdr(org.slug),
            )
        assert r.status_code == 200, r.content
        body = r.json()
        items = body if isinstance(body, list) else body.get("results", body)
        assert len(items) == 1
        assert items[0]["supervisor_membership"] == uh_membership.id

    def test_list_is_tenant_scoped(
        self, api, org, other_org, other_program, admin_user, uh_membership,
        counselor_membership,
    ):
        Supervision.all_objects.create(
            supervisor_membership=uh_membership,
            target_type="membership",
            target_membership=counselor_membership,
            start_date=date(2026, 6, 1),
        )
        foreign_uh = Membership.all_objects.create(
            program=other_program,
            person=Person.all_objects.create(
                organization=other_org, first_name="F", last_name="U",
            ),
            role="unit_head",
            is_active=True,
        )
        foreign_cn = Membership.all_objects.create(
            program=other_program,
            person=Person.all_objects.create(
                organization=other_org, first_name="F", last_name="C",
            ),
            role="counselor",
            is_active=True,
        )
        Supervision.all_objects.create(
            supervisor_membership=foreign_uh,
            target_type="membership",
            target_membership=foreign_cn,
            start_date=date(2026, 6, 1),
        )
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.get("/api/v1/supervisions/", **_hdr(org.slug))
        items = r.json()
        items = items if isinstance(items, list) else items.get("results", items)
        # Only the local row should be visible.
        assert len(items) == 1


# ---------------------------------------------------------------------------
# Mutation: validation errors propagate
# ---------------------------------------------------------------------------


class TestSupervisionCreateValidation:
    def test_counselor_as_supervisor_returns_400(
        self, api, org, admin_user, counselor_membership,
    ):
        other_cn = Membership.all_objects.create(
            program=counselor_membership.program,
            person=Person.all_objects.create(
                organization=org, first_name="C2", last_name="X",
            ),
            role="counselor",
            is_active=True,
        )
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.post(
                "/api/v1/supervisions/",
                {
                    "supervisor_membership": counselor_membership.id,
                    "target_type": "membership",
                    "target_membership": other_cn.id,
                    "start_date": "2026-06-01",
                },
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 400
        assert "supervisor_membership" in r.json()


# ---------------------------------------------------------------------------
# Mutation: end-date PATCH path
# ---------------------------------------------------------------------------


class TestSupervisionPatch:
    def test_end_date_only_path_writes_event(
        self, api, org, admin_user, uh_membership, counselor_membership,
    ):
        sup = Supervision.all_objects.create(
            supervisor_membership=uh_membership,
            target_type="membership",
            target_membership=counselor_membership,
            start_date=date(2026, 6, 1),
        )
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.patch(
                f"/api/v1/supervisions/{sup.id}/",
                {"end_date": "2026-07-01"},
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 200, r.content
        sup.refresh_from_db()
        assert sup.end_date == date(2026, 7, 1)
        assert SupervisionEvent.all_objects.filter(
            supervision=sup, event_type="ended",
        ).count() == 1

    def test_cannot_patch_supervisor(
        self, api, org, admin_user, uh_membership, counselor_membership,
    ):
        other_uh = Membership.all_objects.create(
            program=uh_membership.program,
            person=Person.all_objects.create(
                organization=org, first_name="U2", last_name="X",
            ),
            role="unit_head",
            is_active=True,
        )
        sup = Supervision.all_objects.create(
            supervisor_membership=uh_membership,
            target_type="membership",
            target_membership=counselor_membership,
            start_date=date(2026, 6, 1),
        )
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.patch(
                f"/api/v1/supervisions/{sup.id}/",
                {"supervisor_membership": other_uh.id},
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 400
        assert "supervisor_membership" in r.json()

    def test_patch_must_include_end_date(
        self, api, org, admin_user, uh_membership, counselor_membership,
    ):
        sup = Supervision.all_objects.create(
            supervisor_membership=uh_membership,
            target_type="membership",
            target_membership=counselor_membership,
            start_date=date(2026, 6, 1),
        )
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.patch(
                f"/api/v1/supervisions/{sup.id}/",
                {},
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 400
        assert "end_date" in r.json()


# ---------------------------------------------------------------------------
# DELETE is not allowed
# ---------------------------------------------------------------------------


class TestSupervisionNoDelete:
    def test_delete_returns_method_not_allowed(
        self, api, org, admin_user, uh_membership, counselor_membership,
    ):
        sup = Supervision.all_objects.create(
            supervisor_membership=uh_membership,
            target_type="membership",
            target_membership=counselor_membership,
            start_date=date(2026, 6, 1),
        )
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.delete(
                f"/api/v1/supervisions/{sup.id}/", **_hdr(org.slug),
            )
        assert r.status_code == 405
