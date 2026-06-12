"""API tests for Step 7_13 PR2 -- People + Assignments + Programs/Settings.

Covers, per the lean test recipe (happy path + auth/perm + critical edge):

* People CRUD + email conflict + immutable membership.role
* Assignments backdated safety invariant + conflict warnings
* Programs `end` transaction (atomicity, memberships deactivated, open
  orders/tickets closed, audit rows written, refuses with open flags)
* Settings PATCH writes an AuditEvent
"""

from __future__ import annotations

from datetime import date
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AuditEvent
from bunk_logs.core.models import Flag
from bunk_logs.core.models import MaintenanceTicket
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Order
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Supervision
from bunk_logs.core.state_machine import OrderStateMachine

User = get_user_model()
pytestmark = pytest.mark.django_db


def _hdr(slug: str) -> dict:
    return {"HTTP_X_ORGANIZATION_SLUG": slug}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def api() -> APIClient:
    return APIClient()


@pytest.fixture
def org():
    return Organization.objects.create(name="PR2 Org", slug="pr2-org")


@pytest.fixture
def other_org():
    return Organization.objects.create(name="PR2 Other", slug="pr2-other")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org, name="PR2 Org Summer", slug="pr2-org-summer",
        program_type="summer_camp",
        start_date=date(2026, 6, 1), end_date=date(2026, 8, 31),
    )


@pytest.fixture
def admin_user(org, program):
    u = User.objects.create_user(email="admin-pr2@example.com", password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="Ad", last_name="Min", user=u,
    )
    Membership.all_objects.create(
        program=program, person=person, role="admin", is_active=True,
    )
    return u


@pytest.fixture
def non_admin_user(org, program):
    u = User.objects.create_user(email="other-pr2@example.com", password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="Co", last_name="Un", user=u,
    )
    Membership.all_objects.create(
        program=program, person=person, role="counselor", is_active=True,
    )
    return u


@pytest.fixture
def existing_person(org):
    return Person.all_objects.create(
        organization=org, first_name="Du", last_name="Plicate",
        email="duplicate@example.com",
    )


# ---------------------------------------------------------------------------
# People
# ---------------------------------------------------------------------------


class TestAdminPeople:
    URL = "/api/v1/admin/people/"

    def test_non_admin_blocked(self, api, org, non_admin_user):
        api.force_authenticate(user=non_admin_user)
        with organization_context(org):
            r = api.get(self.URL, **_hdr(org.slug))
        assert r.status_code == 403

    def test_create_person_and_membership(self, api, org, program, admin_user):
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.post(self.URL, {
                "first_name": "New",
                "last_name": "Person",
                "email": "newp@example.com",
                "membership": {
                    "program_id": program.id,
                    "role": "counselor",
                    "tags": ["NEW", "new", " "],
                },
            }, format="json", **_hdr(org.slug))
        assert r.status_code == 201, r.content
        body = r.json()
        assert body["full_name"]
        assert body["memberships"][0]["role"] == "counselor"
        # Tag normalization deduplicates and lowercases.
        assert body["memberships"][0]["tags"] == ["new"]

    def test_email_conflict_returns_409_with_existing(
        self, api, org, program, admin_user, existing_person,
    ):
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.post(self.URL, {
                "first_name": "Another",
                "last_name": "Person",
                "email": "duplicate@example.com",
                "membership": {"program_id": program.id, "role": "counselor"},
            }, format="json", **_hdr(org.slug))
        assert r.status_code == 409
        body = r.json()
        assert body["existing_person"]["id"] == existing_person.id

    def test_list_pagination_and_last_name_initial(
        self, api, org, program, admin_user,
    ):
        with organization_context(org):
            for last_name, first_name in [
                ("Adams", "Amy"),
                ("Brown", "Ben"),
                ("Adams", "Zoe"),
            ]:
                person = Person.all_objects.create(
                    organization=org,
                    first_name=first_name,
                    last_name=last_name,
                )
                Membership.all_objects.create(
                    program=program, person=person, role="counselor", is_active=True,
                )
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            page1 = api.get(
                self.URL,
                {"offset": 0, "page_size": 2},
                **_hdr(org.slug),
            )
            assert page1.status_code == 200
            body1 = page1.json()
            assert body1["count"] == 4  # admin + 3 created
            assert body1["page_size"] == 2
            assert len(body1["results"]) == 2
            assert body1["results"][0]["last_name"] == "Adams"
            assert body1["results"][1]["last_name"] == "Adams"

            page2 = api.get(
                self.URL,
                {"offset": 2, "page_size": 2},
                **_hdr(org.slug),
            )
            assert page2.status_code == 200
            assert len(page2.json()["results"]) == 2

            filtered = api.get(
                self.URL,
                {"last_name_initial": "b", "status": "active"},
                **_hdr(org.slug),
            )
        assert filtered.status_code == 200
        names = [row["full_name"] for row in filtered.json()["results"]]
        assert names == ["Ben Brown"]

    def test_membership_role_is_immutable(
        self, api, org, program, admin_user, existing_person,
    ):
        with organization_context(org):
            m = Membership.all_objects.create(
                program=program, person=existing_person, role="counselor",
                is_active=True,
            )
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.patch(
                f"/api/v1/admin/memberships/{m.id}/",
                {"role": "admin", "tags": ["VIP"]},
                format="json", **_hdr(org.slug),
            )
        assert r.status_code == 200
        m.refresh_from_db()
        assert m.role == "counselor"
        assert m.tags == ["vip"]

    def test_deactivate_membership_audited(
        self, api, org, program, admin_user, existing_person,
    ):
        with organization_context(org):
            m = Membership.all_objects.create(
                program=program, person=existing_person, role="counselor",
                is_active=True,
            )
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.post(
                f"/api/v1/admin/memberships/{m.id}/deactivate/",
                {"reason": "Left mid-summer"},
                format="json", **_hdr(org.slug),
            )
        assert r.status_code == 200
        m.refresh_from_db()
        assert m.is_active is False
        assert AuditEvent.all_objects.filter(
            content_type="membership", content_id=str(m.id),
            event_type=AuditEvent.EventType.DEACTIVATED,
        ).exists()

    def test_invite_requires_email(
        self, api, org, program, admin_user,
    ):
        with organization_context(org):
            p = Person.all_objects.create(
                organization=org, first_name="No", last_name="Email",
            )
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.post(
                f"/api/v1/admin/people/{p.id}/invite/", {},
                format="json", **_hdr(org.slug),
            )
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Assignments
# ---------------------------------------------------------------------------


class TestAdminAssignments:
    URL = "/api/v1/admin/assignments/"

    @pytest.fixture
    def supervisor(self, org, program):
        person = Person.all_objects.create(
            organization=org, first_name="Sue", last_name="Per",
        )
        return Membership.all_objects.create(
            program=program, person=person, role="unit_head", is_active=True,
        )

    @pytest.fixture
    def target(self, org, program):
        person = Person.all_objects.create(
            organization=org, first_name="Ta", last_name="Rget",
        )
        return Membership.all_objects.create(
            program=program, person=person, role="counselor", is_active=True,
        )

    def test_non_admin_blocked(self, api, org, non_admin_user):
        api.force_authenticate(user=non_admin_user)
        with organization_context(org):
            r = api.get(self.URL, **_hdr(org.slug))
        assert r.status_code == 403

    def test_backdated_start_is_clamped(
        self, api, org, admin_user, supervisor, target,
    ):
        api.force_authenticate(user=admin_user)
        backdate = "2020-01-01"
        with organization_context(org):
            r = api.post(self.URL, {
                "sub_tab": "uh_counselor",
                "supervisor_membership_id": supervisor.id,
                "target_membership_id": target.id,
                "start_date": backdate,
            }, format="json", **_hdr(org.slug))
        assert r.status_code == 201, r.content
        body = r.json()
        assert body["backdated_clamped"] is True
        assert body["requested_start_date"] == backdate
        # Effective start clamped away from the far-past date (>= 2026-01-01).
        # Allow one day of slack for UTC-midnight edge cases.
        sup_id = body["supervision"]["id"]
        sup = Supervision.all_objects.get(pk=sup_id)
        assert sup.start_date >= date.today() - timedelta(days=1)

    def test_conflict_warning_surfaced(
        self, api, org, admin_user, supervisor, target,
    ):
        api.force_authenticate(user=admin_user)
        payload = {
            "sub_tab": "uh_counselor",
            "supervisor_membership_id": supervisor.id,
            "target_membership_id": target.id,
        }
        with organization_context(org):
            r1 = api.post(self.URL, payload, format="json", **_hdr(org.slug))
            assert r1.status_code == 201
            r2 = api.post(self.URL, payload, format="json", **_hdr(org.slug))
        assert r2.status_code == 201
        # The second create on the same target/supervisor pair surfaces
        # the first as a co-supervisor warning.
        assert any(
            w["kind"] == "co_supervisor"
            for w in r2.json()["warnings"]
        )

    def test_group_membership_create_and_conflict(
        self, api, org, program, admin_user,
    ):
        with organization_context(org):
            group = AssignmentGroup.all_objects.create(
                organization=org, program=program, name="Bunk 1",
                slug="bunk-1", group_type="bunk",
            )
            person = Person.all_objects.create(
                organization=org, first_name="Pa", last_name="Rt",
            )
        api.force_authenticate(user=admin_user)
        payload = {
            "sub_tab": "counselor_bunk",
            "group_id": group.id,
            "person_id": person.id,
        }
        with organization_context(org):
            r1 = api.post(self.URL, payload, format="json", **_hdr(org.slug))
            r2 = api.post(self.URL, payload, format="json", **_hdr(org.slug))
        assert r1.status_code == 201
        assert r2.status_code == 409

    def test_uh_unit_group_membership_create_and_list(
        self, api, org, program, admin_user,
    ):
        with organization_context(org):
            unit = AssignmentGroup.all_objects.create(
                organization=org, program=program, name="Unit Alef",
                slug="unit-alef", group_type="unit",
            )
            uh_person = Person.all_objects.create(
                organization=org, first_name="Uh", last_name="Lead",
            )
        api.force_authenticate(user=admin_user)
        payload = {
            "sub_tab": "uh_unit",
            "group_id": unit.id,
            "person_id": uh_person.id,
        }
        with organization_context(org):
            created = api.post(self.URL, payload, format="json", **_hdr(org.slug))
            assert created.status_code == 201, created.content
            listed = api.get(
                self.URL,
                {"sub_tab": "uh_unit", "program": program.id, "status": "active"},
                **_hdr(org.slug),
            )
        assert listed.status_code == 200
        rows = listed.json()["results"]
        assert len(rows) == 1
        assert rows[0]["group_name"] == "Unit Alef"
        assert rows[0]["person_name"] == uh_person.full_name
        assert rows[0]["sub_tab"] == "uh_unit"

    def test_list_filters_by_program_and_status(
        self, api, org, program, admin_user, supervisor, target,
    ):
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            active = api.post(self.URL, {
                "sub_tab": "uh_counselor",
                "supervisor_membership_id": supervisor.id,
                "target_membership_id": target.id,
            }, format="json", **_hdr(org.slug))
            assert active.status_code == 201
            listed = api.get(
                self.URL,
                {
                    "sub_tab": "uh_counselor",
                    "program": program.id,
                    "status": "active",
                    "search": "Rget",
                },
                **_hdr(org.slug),
            )
        assert listed.status_code == 200
        assert len(listed.json()["results"]) == 1
        row = listed.json()["results"][0]
        assert row["target_membership_name"] == "Ta Rget"
        assert row["supervisor_role"] == "unit_head"
        assert row["target_membership_role"] == "counselor"

    def test_staff_team_membership_create_and_list(
        self, api, org, program, admin_user,
    ):
        with organization_context(org):
            team = AssignmentGroup.all_objects.create(
                organization=org, program=program, name="Kitchen Staff",
                slug="kitchen-staff", group_type="team",
            )
            person = Person.all_objects.create(
                organization=org, first_name="Kit", last_name="Chen",
            )
            Membership.all_objects.create(
                program=program, person=person, role="kitchen_staff", is_active=True,
            )
        api.force_authenticate(user=admin_user)
        payload = {
            "sub_tab": "staff_team",
            "group_id": team.id,
            "person_id": person.id,
        }
        with organization_context(org):
            r = api.post(self.URL, payload, format="json", **_hdr(org.slug))
            assert r.status_code == 201, r.content
            assert r.json()["assignment_group_membership"]["sub_tab"] == "staff_team"
            listed = api.get(
                self.URL, {"sub_tab": "staff_team"}, **_hdr(org.slug),
            )
        assert listed.status_code == 200
        rows = listed.json()["results"]
        assert len(rows) == 1
        assert rows[0]["sub_tab"] == "staff_team"
        assert rows[0]["group_id"] == team.id
        assert rows[0]["membership_role"] == "kitchen_staff"

    def test_staff_team_rejects_non_team_group(
        self, api, org, program, admin_user,
    ):
        with organization_context(org):
            bunk = AssignmentGroup.all_objects.create(
                organization=org, program=program, name="Bunk 2",
                slug="bunk-2", group_type="bunk",
            )
            person = Person.all_objects.create(
                organization=org, first_name="No", last_name="Match",
            )
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.post(
                self.URL,
                {
                    "sub_tab": "staff_team",
                    "group_id": bunk.id,
                    "person_id": person.id,
                },
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 400
        assert "team group" in r.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Programs + End Program
# ---------------------------------------------------------------------------


class TestAdminPrograms:
    URL = "/api/v1/admin/programs/"

    def test_list_and_create(self, api, org, admin_user):
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.post(self.URL, {
                "name": "PR2 Org Brand New",
                "slug": "pr2-brand-new",
                "program_type": "summer_camp",
                "start_date": "2026-09-01",
                "end_date": "2027-08-31",
            }, format="json", **_hdr(org.slug))
        assert r.status_code == 201, r.content
        with organization_context(org):
            r2 = api.get(self.URL, **_hdr(org.slug))
        assert r2.status_code == 200
        slugs = {p["slug"] for p in r2.json()["results"]}
        assert "pr2-brand-new" in slugs

    def test_end_program_runs_in_transaction(
        self, api, org, program, admin_user,
    ):
        # Seed: an active counselor membership + open order + open ticket.
        with organization_context(org):
            cperson = Person.all_objects.create(
                organization=org, first_name="To", last_name="End",
            )
            cm = Membership.all_objects.create(
                program=program, person=cperson, role="counselor", is_active=True,
            )
            o = Order.objects.create(
                organization=org, program=program,
                submitted_by=cm,
                status=OrderStateMachine.NEW,
            )
            t = MaintenanceTicket.objects.create(
                organization=org, program=program,
                submitted_by=cm,
                status=OrderStateMachine.NEW,
            )
        api.force_authenticate(user=admin_user)
        url = f"/api/v1/admin/programs/{program.id}/end/"
        with organization_context(org):
            r = api.post(url, {"reason": "Season over"}, format="json", **_hdr(org.slug))
        assert r.status_code == 200, r.content
        body = r.json()
        assert body["summary"]["memberships_deactivated"] >= 1
        assert body["summary"]["orders_closed"] >= 1
        assert body["summary"]["maintenance_tickets_closed"] >= 1
        cm.refresh_from_db()
        o.refresh_from_db()
        t.refresh_from_db()
        assert cm.is_active is False
        assert o.status == OrderStateMachine.UNABLE_TO_FULFILL
        assert t.status == OrderStateMachine.UNABLE_TO_FULFILL
        program.refresh_from_db()
        assert program.is_active is False

    def test_end_program_refused_with_open_flags(
        self, api, org, program, admin_user,
    ):
        with organization_context(org):
            subject = Person.all_objects.create(
                organization=org, first_name="Sub", last_name="J",
            )
            cc_person = Person.all_objects.create(
                organization=org, first_name="Cc", last_name="Per",
            )
            cc_m = Membership.all_objects.create(
                program=program, person=cc_person, role="camper_care", is_active=True,
            )
            Flag.objects.create(
                organization=org, program=program,
                subject_camper=subject, raised_by_membership=cc_m,
                flagged_for_role="camper_care",
            )
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.post(
                f"/api/v1/admin/programs/{program.id}/end/",
                {"reason": "Trying"}, format="json", **_hdr(org.slug),
            )
        assert r.status_code == 400
        program.refresh_from_db()
        assert program.is_active is True

    def test_end_program_rolls_back_on_unexpected_failure(
        self, api, org, program, admin_user,
    ):
        # Inject a runtime error inside the End Program transaction
        # via the override_close audit helper. The transaction must
        # roll back so the program stays active, no memberships get
        # deactivated, and no orders get closed.
        with organization_context(org):
            cperson = Person.all_objects.create(
                organization=org, first_name="X", last_name="Y",
            )
            cm = Membership.all_objects.create(
                program=program, person=cperson, role="counselor", is_active=True,
            )
            o = Order.objects.create(
                organization=org, program=program,
                submitted_by=cm, status=OrderStateMachine.NEW,
            )
        api.force_authenticate(user=admin_user)
        api.raise_request_exception = False
        with patch(
            "bunk_logs.api.admin_flow.programs.audit_module.override_close",
            side_effect=RuntimeError("boom"),
        ), organization_context(org):
            r = api.post(
                f"/api/v1/admin/programs/{program.id}/end/",
                {"reason": "Should rollback"},
                format="json", **_hdr(org.slug),
            )
        # The view doesn't catch this exception, so DRF surfaces it as
        # an HTTP 500. The important assertion is the rollback below.
        assert r.status_code == 500
        program.refresh_from_db()
        cm.refresh_from_db()
        o.refresh_from_db()
        assert program.is_active is True
        assert cm.is_active is True
        assert o.status == OrderStateMachine.NEW


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


class TestAdminSettings:
    URL = "/api/v1/admin/settings/"

    def test_get_returns_settings(self, api, org, admin_user):
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.get(self.URL, **_hdr(org.slug))
        assert r.status_code == 200
        body = r.json()
        assert body["organization_id"] == org.id
        assert body["slug"] == org.slug

    def test_patch_writes_audit(self, api, org, admin_user):
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.patch(self.URL, {
                "supported_languages": ["en", "es"],
                "rollover_hour": 4,
            }, format="json", **_hdr(org.slug))
        assert r.status_code == 200
        body = r.json()
        assert body["settings"]["supported_languages"] == ["en", "es"]
        assert body["settings"]["rollover_hour"] == 4
        assert AuditEvent.all_objects.filter(
            content_type="organization_settings", content_id=str(org.id),
        ).exists()
