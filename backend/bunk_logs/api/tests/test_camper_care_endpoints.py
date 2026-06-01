"""Tests for ``/api/v1/camper-care/*`` (Step 7_8, Stories 18-23).

Coverage targets per lean mode:

* Happy + auth + critical edge per endpoint.
* Flag lifecycle (Active -> Followed Up -> Resolved -> Reopen) with
  audit trail.
* Order workspace team-shared visibility (CC7) -- every CC member in a
  program sees the same queue regardless of caseload.
* Flag workspace trigger preview resolves migrated observations.
"""

from __future__ import annotations

from datetime import date
from datetime import timedelta
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import AuditEvent
from bunk_logs.core.models import Flag
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Order
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import Supervision
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
    return Organization.objects.create(name="CC Org", slug="cc-org")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="CC Org Summer 2026",
        slug="cc-summer-2026",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


def _make_person(org, *, first, last, email):
    user = User.objects.create_user(email=email, password="pw")
    person = Person.all_objects.create(
        organization=org, first_name=first, last_name=last, user=user,
    )
    return person, user


def _make_membership(program, person, role):
    return Membership.all_objects.create(
        program=program, person=person, role=role, is_active=True,
    )


@pytest.fixture
def cc_person_user(org):
    return _make_person(org, first="Pat", last="Coster", email="cc@cc.test")


@pytest.fixture
def cc_membership(program, cc_person_user):
    person, _ = cc_person_user
    return _make_membership(program, person, "camper_care")


@pytest.fixture
def cc2_person_user(org):
    return _make_person(org, first="Sam", last="Wright", email="cc2@cc.test")


@pytest.fixture
def cc2_membership(program, cc2_person_user):
    person, _ = cc2_person_user
    return _make_membership(program, person, "camper_care")


@pytest.fixture
def counselor_person_user(org):
    return _make_person(org, first="Mira", last="Levi", email="co@cc.test")


@pytest.fixture
def admin_person_user(org):
    return _make_person(org, first="Ada", last="Min", email="admin@cc.test")


@pytest.fixture
def admin_membership(program, admin_person_user):
    person, _ = admin_person_user
    return _make_membership(program, person, "admin")


@pytest.fixture
def counselor_membership(program, counselor_person_user):
    person, _ = counselor_person_user
    return _make_membership(program, person, "counselor")


@pytest.fixture
def uh_person_user(org):
    return _make_person(org, first="Avery", last="Reeves", email="uh@cc.test")


@pytest.fixture
def uh_membership(program, uh_person_user):
    person, _ = uh_person_user
    return _make_membership(program, person, "unit_head")


@pytest.fixture
def unit(org, program):
    return AssignmentGroup.all_objects.create(
        organization=org, program=program,
        name="Unit Alef", slug="unit-alef", group_type="unit", is_active=True,
    )


@pytest.fixture
def bunk(org, program, unit):
    return AssignmentGroup.all_objects.create(
        organization=org, program=program,
        name="Bunk Birch", slug="bunk-birch", group_type="bunk",
        parent=unit, is_active=True,
    )


@pytest.fixture
def other_bunk(org, program, unit):
    return AssignmentGroup.all_objects.create(
        organization=org, program=program,
        name="Bunk Pine", slug="bunk-pine", group_type="bunk",
        parent=unit, is_active=True,
    )


@pytest.fixture
def cc_caseload(cc_membership, bunk):
    return Supervision.all_objects.create(
        supervisor_membership=cc_membership,
        target_type="bunk",
        target_bunk=bunk,
        start_date=date(2026, 1, 1),
    )


@pytest.fixture
def cc2_other_caseload(cc2_membership, other_bunk):
    """Second CC member with a DIFFERENT bunk -- proves team-shared CC7."""
    return Supervision.all_objects.create(
        supervisor_membership=cc2_membership,
        target_type="bunk",
        target_bunk=other_bunk,
        start_date=date(2026, 1, 1),
    )


@pytest.fixture
def camper(org):
    return Person.all_objects.create(
        organization=org, first_name="Sarah", last_name="Levin",
    )


@pytest.fixture
def camper_in_bunk(camper, bunk):
    return AssignmentGroupMembership.all_objects.create(
        group=bunk, person=camper, role_in_group="subject", is_active=True,
    )


@pytest.fixture
def api():
    return APIClient()


# ---------------------------------------------------------------------------
# Dashboard (Story 18 / 19)
# ---------------------------------------------------------------------------


class TestCamperCareDashboard:
    def test_returns_caseload_tree(
        self, api, org, cc_person_user, cc_membership, cc_caseload,
        bunk, unit, camper, camper_in_bunk,
    ):
        _, user = cc_person_user
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get("/api/v1/camper-care/dashboard/", **_hdr(org.slug))
        assert r.status_code == 200, r.content
        body = r.json()
        assert body["today"]
        units = body["units"]
        assert len(units) == 1
        u = units[0]
        assert u["name"] == "Unit Alef"
        assert len(u["bunks"]) == 1
        assert u["bunks"][0]["id"] == bunk.id
        assert u["bunks"][0]["camper_count"] == 1
        # Summary counts present
        assert body["summary"]["flag_count"] == 0
        assert body["summary"]["order_count"] == 0

    def test_requires_camper_care_role(
        self, api, org, counselor_person_user, counselor_membership,
    ):
        _, user = counselor_person_user
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get("/api/v1/camper-care/dashboard/", **_hdr(org.slug))
        assert r.status_code == 403

    def test_unauthenticated_rejected(self, api, org):
        with organization_context(org):
            r = api.get("/api/v1/camper-care/dashboard/", **_hdr(org.slug))
        assert r.status_code in (401, 403)

    def test_future_date_rejected(
        self, api, org, cc_person_user, cc_membership, cc_caseload,
    ):
        _, user = cc_person_user
        api.force_authenticate(user=user)
        future = (date.today() + timedelta(days=5)).isoformat()
        with organization_context(org):
            r = api.get(
                f"/api/v1/camper-care/dashboard/?date={future}", **_hdr(org.slug),
            )
        assert r.status_code == 400

    def test_unresolved_flag_count_in_summary(
        self, api, org, program, cc_person_user, cc_membership, cc_caseload,
        camper, camper_in_bunk,
    ):
        Flag.all_objects.create(
            organization=org, program=program, subject_camper=camper,
            flagged_for_role="camper_care",
            status=Flag.Status.ACTIVE,
        )
        Flag.all_objects.create(
            organization=org, program=program, subject_camper=camper,
            flagged_for_role="camper_care",
            status=Flag.Status.RESOLVED, resolved_at=timezone.now(),
        )
        _, user = cc_person_user
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get("/api/v1/camper-care/dashboard/", **_hdr(org.slug))
        assert r.status_code == 200
        assert r.json()["summary"]["flag_count"] == 1


# ---------------------------------------------------------------------------
# Flag lifecycle (Story 20)
# ---------------------------------------------------------------------------


class TestFlagLifecycle:
    def test_active_to_followed_up_to_resolved_to_reopen(
        self, api, org, program, cc_person_user, cc_membership, camper,
    ):
        flag = Flag.all_objects.create(
            organization=org, program=program, subject_camper=camper,
            flagged_for_role="camper_care",
        )
        _, user = cc_person_user
        api.force_authenticate(user=user)

        with organization_context(org):
            # Active -> Followed Up
            r = api.post(
                f"/api/v1/camper-care/flags/{flag.id}/follow-up/",
                {"note": "checked in with bunk staff"},
                format="json", **_hdr(org.slug),
            )
            assert r.status_code == 200, r.content
            assert r.json()["flag"]["status"] == Flag.Status.FOLLOWED_UP

            # Followed Up -> Resolved (note required)
            r = api.post(
                f"/api/v1/camper-care/flags/{flag.id}/resolve/",
                {"note": "Resolved after family conversation"},
                format="json", **_hdr(org.slug),
            )
            assert r.status_code == 200, r.content
            assert r.json()["flag"]["status"] == Flag.Status.RESOLVED
            assert r.json()["flag"]["resolved_at"] is not None

            # Resolved -> Active (reopen, reason required)
            r = api.post(
                f"/api/v1/camper-care/flags/{flag.id}/reopen/",
                {"note": "New concern from counselor"},
                format="json", **_hdr(org.slug),
            )
            assert r.status_code == 200, r.content
            assert r.json()["flag"]["status"] == Flag.Status.ACTIVE
            assert r.json()["flag"]["resolved_at"] is None

        # Audit trail: 3 STATE_CHANGED rows (one per transition)
        events = AuditEvent.all_objects.filter(
            content_type="flag", content_id=str(flag.id),
            event_type=AuditEvent.EventType.STATE_CHANGED,
        ).order_by("created_at")
        assert events.count() == 3

    def test_resolve_without_note_400(
        self, api, org, program, cc_person_user, cc_membership, camper,
    ):
        flag = Flag.all_objects.create(
            organization=org, program=program, subject_camper=camper,
            flagged_for_role="camper_care",
        )
        _, user = cc_person_user
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.post(
                f"/api/v1/camper-care/flags/{flag.id}/resolve/", {},
                format="json", **_hdr(org.slug),
            )
        assert r.status_code == 400
        assert "note" in r.json()

    def test_reopen_from_active_not_allowed(
        self, api, org, program, cc_person_user, cc_membership, camper,
    ):
        flag = Flag.all_objects.create(
            organization=org, program=program, subject_camper=camper,
            flagged_for_role="camper_care",
            status=Flag.Status.ACTIVE,
        )
        _, user = cc_person_user
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.post(
                f"/api/v1/camper-care/flags/{flag.id}/reopen/",
                {"note": "irrelevant"},
                format="json", **_hdr(org.slug),
            )
        assert r.status_code == 400  # Active -> Active not in transition table

    def test_counselor_cannot_resolve(
        self, api, org, program, counselor_person_user, counselor_membership,
        camper,
    ):
        flag = Flag.all_objects.create(
            organization=org, program=program, subject_camper=camper,
            flagged_for_role="camper_care",
        )
        _, user = counselor_person_user
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.post(
                f"/api/v1/camper-care/flags/{flag.id}/resolve/",
                {"note": "trying as counselor"},
                format="json", **_hdr(org.slug),
            )
        assert r.status_code == 403  # CC3

    def test_flag_list_default_excludes_resolved(
        self, api, org, program, cc_person_user, cc_membership, camper,
    ):
        Flag.all_objects.create(
            organization=org, program=program, subject_camper=camper,
            flagged_for_role="camper_care", status=Flag.Status.ACTIVE,
        )
        Flag.all_objects.create(
            organization=org, program=program, subject_camper=camper,
            flagged_for_role="camper_care", status=Flag.Status.RESOLVED,
            resolved_at=timezone.now(),
        )
        _, user = cc_person_user
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get("/api/v1/camper-care/flags/", **_hdr(org.slug))
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) == 1
        assert items[0]["status"] == Flag.Status.ACTIVE


# ---------------------------------------------------------------------------
# Orders workspace -- team shared (CC7)
# ---------------------------------------------------------------------------


class TestCamperCareOrdersTeamShared:
    def test_admin_can_list_program_orders(
        self, api, org, program, admin_person_user, admin_membership, camper,
    ):
        Order.all_objects.create(
            organization=org, program=program, subject=camper, item="Soap",
        )
        _, user = admin_person_user
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get("/api/v1/camper-care/orders/", **_hdr(org.slug))
        assert r.status_code == 200, r.content
        assert len(r.json()["new"]) == 1

    def test_both_cc_members_see_same_orders(
        self, api, org, program, cc_person_user, cc_membership,
        cc2_person_user, cc2_membership, camper, bunk, other_bunk,
    ):
        # Camper Care #1 supervises bunk (where camper lives); CC #2
        # supervises other_bunk. Order is bound to the camper in bunk.
        # CC2 should STILL see it because workspace is team-shared per CC7.
        Order.all_objects.create(
            organization=org, program=program, subject=camper, item="Toothbrush",
        )
        _, cc1_user = cc_person_user
        _, cc2_user = cc2_person_user

        api.force_authenticate(user=cc1_user)
        with organization_context(org):
            r1 = api.get("/api/v1/camper-care/orders/", **_hdr(org.slug))
        assert r1.status_code == 200
        assert len(r1.json()["new"]) == 1

        api.force_authenticate(user=cc2_user)
        with organization_context(org):
            r2 = api.get("/api/v1/camper-care/orders/", **_hdr(org.slug))
        assert r2.status_code == 200
        assert len(r2.json()["new"]) == 1

    def test_my_caseload_filter_narrows_to_supervised_campers(
        self, api, org, program, cc_person_user, cc_membership, cc_caseload,
        cc2_person_user, cc2_membership, cc2_other_caseload,
        camper, camper_in_bunk,
    ):
        # Camper is in `bunk` (CC1's caseload). Order is for camper.
        Order.all_objects.create(
            organization=org, program=program, subject=camper, item="Bandaid",
        )
        # CC2 (different caseload) filtered to my_caseload sees nothing.
        _, cc2_user = cc2_person_user
        api.force_authenticate(user=cc2_user)
        with organization_context(org):
            r = api.get(
                "/api/v1/camper-care/orders/?filter=my_caseload",
                **_hdr(org.slug),
            )
        assert r.status_code == 200
        assert len(r.json()["new"]) == 0

    def test_transition_via_camper_care_alias(
        self, api, org, program, cc_person_user, cc_membership, camper,
    ):
        order = Order.all_objects.create(
            organization=org, program=program, subject=camper, item="Toothbrush",
        )
        _, user = cc_person_user
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.post(
                f"/api/v1/camper-care/orders/{order.id}/transition/",
                {"to_state": "in_progress", "note": "picked up"},
                format="json", **_hdr(org.slug),
            )
        assert r.status_code == 200, r.content
        order.refresh_from_db()
        assert order.status == "in_progress"

    def test_bulk_fulfill(
        self, api, org, program, cc_person_user, cc_membership, camper,
    ):
        ids = []
        for _ in range(3):
            o = Order.all_objects.create(
                organization=org, program=program, subject=camper, item="X",
            )
            with organization_context(org):
                o.transition_to("in_progress", actor=cc_membership)
            ids.append(str(o.id))
        _, user = cc_person_user
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.post(
                "/api/v1/camper-care/orders/bulk-transition/",
                {"ids": ids, "to_state": "fulfilled", "note": "batch fulfill"},
                format="json", **_hdr(org.slug),
            )
        assert r.status_code == 200, r.content
        assert len(r.json()["transitioned"]) == 3


# ---------------------------------------------------------------------------
# Bunk + Camper drill-down (Step 7_8c) — Story 18 c.9 + Story 21 in-context
# ---------------------------------------------------------------------------


class TestCamperCareBunkDashboard:
    """``GET /api/v1/camper-care/bunks/<id>/`` — Story 18 criterion 9.

    Reuses the shared `build_bunk_dashboard_payload` extracted from the
    UH view, so we only test the CC-specific gate + payload shape here.
    The UH bunk dashboard tests already cover the section contracts.
    """

    def test_returns_payload_for_bunk_on_caseload(
        self, api, org, cc_person_user, cc_membership, cc_caseload,
        bunk, unit, camper, camper_in_bunk,
    ):
        _, user = cc_person_user
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get(
                f"/api/v1/camper-care/bunks/{bunk.id}/", **_hdr(org.slug),
            )
        assert r.status_code == 200, r.content
        body = r.json()
        assert body["header"]["bunk"]["id"] == bunk.id
        assert body["header"]["bunk"]["name"] == bunk.name
        assert body["header"]["bunk"]["unit_name"] == unit.name
        # Section keys present (shape contract from the shared helper).
        for key in (
            "help_requested", "off_camp", "bunk_concerns",
            "score_grid", "orders", "specialist_reports",
        ):
            assert key in body, f"missing section {key!r}"

    def test_bunk_off_caseload_rejected(
        self, api, org, cc_person_user, cc_membership, cc_caseload,
        other_bunk,
    ):
        """CC member with `bunk` on caseload cannot open `other_bunk`."""
        _, user = cc_person_user
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get(
                f"/api/v1/camper-care/bunks/{other_bunk.id}/",
                **_hdr(org.slug),
            )
        assert r.status_code == 403

    def test_requires_camper_care_role(
        self, api, org, counselor_person_user, counselor_membership, bunk,
    ):
        _, user = counselor_person_user
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get(
                f"/api/v1/camper-care/bunks/{bunk.id}/", **_hdr(org.slug),
            )
        assert r.status_code == 403

    def test_future_date_rejected(
        self, api, org, cc_person_user, cc_membership, cc_caseload, bunk,
    ):
        _, user = cc_person_user
        api.force_authenticate(user=user)
        future = (date.today() + timedelta(days=30)).isoformat()
        with organization_context(org):
            r = api.get(
                f"/api/v1/camper-care/bunks/{bunk.id}/?date={future}",
                **_hdr(org.slug),
            )
        assert r.status_code == 400


class TestCamperCareCamperDashboard:
    """``GET /api/v1/camper-care/campers/<id>/`` — Story 18 c.9 + Story 21."""

    def test_returns_payload_for_camper_on_caseload(
        self, api, org, cc_person_user, cc_membership, cc_caseload,
        bunk, camper, camper_in_bunk,
    ):
        _, user = cc_person_user
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get(
                f"/api/v1/camper-care/campers/{camper.id}/", **_hdr(org.slug),
            )
        assert r.status_code == 200, r.content
        body = r.json()
        assert body["header"]["camper"]["id"] == camper.id
        # Section keys present (shape contract from the shared helper).
        for key in (
            "trend", "today_reflection", "today_scores", "today_flags",
            "specialist_reports", "camper_care_notes",
        ):
            assert key in body, f"missing section {key!r}"

    def test_camper_off_caseload_rejected(
        self, api, org, cc_person_user, cc_membership, cc_caseload,
        other_bunk,
    ):
        """Camper rostered to a bunk NOT on viewer's caseload -> 403."""
        # Camper is in `other_bunk`, which is not on cc_membership's caseload.
        outsider = Person.all_objects.create(
            organization=org, first_name="Quinn", last_name="Out",
        )
        AssignmentGroupMembership.all_objects.create(
            group=other_bunk, person=outsider,
            role_in_group="subject", is_active=True,
        )
        _, user = cc_person_user
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get(
                f"/api/v1/camper-care/campers/{outsider.id}/",
                **_hdr(org.slug),
            )
        assert r.status_code == 403

    def test_camper_not_found(
        self, api, org, cc_person_user, cc_membership, cc_caseload,
    ):
        _, user = cc_person_user
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get(
                "/api/v1/camper-care/campers/99999999/", **_hdr(org.slug),
            )
        assert r.status_code == 404

    def test_requires_camper_care_role(
        self, api, org, counselor_person_user, counselor_membership,
        camper, camper_in_bunk,
    ):
        _, user = counselor_person_user
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get(
                f"/api/v1/camper-care/campers/{camper.id}/", **_hdr(org.slug),
            )
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Self-reflection (Step 7_8d) — write + edit + history
# ---------------------------------------------------------------------------


class TestCamperCareSelfReflection:
    """``POST/PATCH/GET /api/v1/camper-care/self-reflection/*``.

    Mirrors UH self-reflection coverage: day-off shortcut, idempotent
    replay, today-only edit window, caseload-gated bunk_concerns, and
    history shape parity.
    """

    def _post(self, api, org, body):
        return api.post(
            "/api/v1/camper-care/self-reflection/",
            data=body, format="json", **_hdr(org.slug),
        )

    def test_day_off_post_creates_complete_row(
        self, api, org, cc_person_user, cc_membership,
    ):
        person, user = cc_person_user
        api.force_authenticate(user=user)
        with organization_context(org):
            r = self._post(api, org, {
                "day_off": True,
                "language": "en",
                "client_submission_id": str(uuid4()),
            })
        assert r.status_code == 201, r.content
        body = r.json()
        assert body["answers"] == {"day_off": True}
        refl = Reflection.all_objects.get(author=person, subject=person)
        assert refl.is_complete

    def test_idempotent_replay_returns_existing(
        self, api, org, cc_person_user, cc_membership,
    ):
        _, user = cc_person_user
        api.force_authenticate(user=user)
        cid = str(uuid4())
        with organization_context(org):
            first = self._post(api, org, {"day_off": True, "client_submission_id": cid})
            assert first.status_code == 201
            replay = self._post(api, org, {"day_off": True, "client_submission_id": cid})
        assert replay.status_code == 200
        assert replay.json()["id"] == first.json()["id"]

    def test_bunk_concerns_rejects_off_caseload_bunk(
        self, api, org, cc_person_user, cc_membership, cc_caseload, other_bunk,
    ):
        """A CC member cannot flag a bunk that's not on their caseload."""
        _, user = cc_person_user
        api.force_authenticate(user=user)
        with organization_context(org):
            r = self._post(api, org, {
                "day_off": False,
                "answers": {
                    "overall_day": 4,
                    "bunk_concerns_bunks": [other_bunk.id],
                },
                "language": "en",
                "client_submission_id": str(uuid4()),
            })
        assert r.status_code == 403

    def test_bunk_concerns_accepts_caseload_bunk(
        self, api, org, cc_person_user, cc_membership, cc_caseload, bunk,
    ):
        person, user = cc_person_user
        api.force_authenticate(user=user)
        with organization_context(org):
            r = self._post(api, org, {
                "day_off": False,
                "answers": {
                    "overall_day": 4,
                    "bunk_concerns_bunks": [bunk.id],
                    "bunk_concerns_note": "Watch sleep schedule.",
                },
                "language": "en",
                "client_submission_id": str(uuid4()),
            })
        assert r.status_code == 201, r.content
        refl = Reflection.all_objects.get(author=person, subject=person)
        assert refl.answers["bunk_concerns_bunks"] == [bunk.id]

    def test_patch_within_today_window(
        self, api, org, program, cc_person_user, cc_membership,
    ):
        person, user = cc_person_user
        template = ReflectionTemplate.all_objects.get(
            slug="camper-care-self-reflection",
        )
        from bunk_logs.core.time_utils import get_today
        today = get_today(org)
        refl = Reflection.all_objects.create(
            organization=org, program=program, template=template,
            subject=person, author=person,
            period_start=today, period_end=today,
            answers={"overall_day": 3}, is_complete=True,
        )
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.patch(
                f"/api/v1/camper-care/self-reflection/{refl.id}/",
                data={"answers": {"overall_day": 5}},
                format="json", **_hdr(org.slug),
            )
        assert r.status_code == 200
        refl.refresh_from_db()
        assert refl.answers["overall_day"] == 5

    def test_patch_outside_window_403(
        self, api, org, program, cc_person_user, cc_membership,
    ):
        person, user = cc_person_user
        template = ReflectionTemplate.all_objects.get(
            slug="camper-care-self-reflection",
        )
        from bunk_logs.core.time_utils import get_today
        today = get_today(org)
        # Backdate so today's window doesn't include it.
        refl = Reflection.all_objects.create(
            organization=org, program=program, template=template,
            subject=person, author=person,
            period_start=today - timedelta(days=1),
            period_end=today - timedelta(days=1),
            answers={"overall_day": 3}, is_complete=True,
        )
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.patch(
                f"/api/v1/camper-care/self-reflection/{refl.id}/",
                data={"answers": {"overall_day": 5}},
                format="json", **_hdr(org.slug),
            )
        assert r.status_code == 403

    def test_history_shows_gaps_and_day_off(
        self, api, org, program, cc_person_user, cc_membership,
    ):
        person, user = cc_person_user
        template = ReflectionTemplate.all_objects.get(
            slug="camper-care-self-reflection",
        )
        from bunk_logs.core.time_utils import get_today
        today = get_today(org)
        Reflection.all_objects.create(
            organization=org, program=program, template=template,
            subject=person, author=person,
            period_start=today - timedelta(days=1),
            period_end=today - timedelta(days=1),
            answers={"day_off": True}, is_complete=True,
        )
        Reflection.all_objects.create(
            organization=org, program=program, template=template,
            subject=person, author=person,
            period_start=today - timedelta(days=3),
            period_end=today - timedelta(days=3),
            answers={"overall_day": 4, "concern": "Long week."},
            is_complete=True,
        )
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get(
                "/api/v1/camper-care/self-reflection/history/", **_hdr(org.slug),
            )
        assert r.status_code == 200
        rows = {row["date"]: row for row in r.json()["results"]}
        yesterday = rows[(today - timedelta(days=1)).isoformat()]
        day_minus_3 = rows[(today - timedelta(days=3)).isoformat()]
        assert yesterday["is_day_off"] is True
        assert yesterday["submitted"] is True
        assert day_minus_3["submitted"] is True
        assert day_minus_3["preview"]

    def test_requires_camper_care_role(
        self, api, org, counselor_person_user, counselor_membership,
    ):
        _, user = counselor_person_user
        api.force_authenticate(user=user)
        with organization_context(org):
            r = self._post(api, org, {
                "day_off": True, "client_submission_id": str(uuid4()),
            })
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Trigger preview + camper-dashboard flag_history (Step 7_8d)
# ---------------------------------------------------------------------------


def _flag_from_observation(org, program, author, camper, body: str) -> Flag:
    obs = Observation.all_objects.create(
        organization=org,
        program=program,
        author=author,
        body=body,
        author_role_at_write="specialist",
    )
    ObservationSubject.objects.create(observation=obs, subject=camper)
    return Flag.all_objects.create(
        organization=org,
        program=program,
        subject_camper=camper,
        flagged_for_role="camper_care",
        trigger_content_type="specialist_note",
        trigger_content_id=str(obs.id),
        status=Flag.Status.ACTIVE,
    )


class TestFlagWorkspaceTriggerPreview:
    def test_specialist_note_trigger_preview_returned(
        self, api, org, program, cc_person_user, cc_membership,
        counselor_person_user, camper,
    ):
        """Workspace list rows include a `trigger_preview` snippet so CC
        can read the source without leaving the workspace.
        """
        author_person, _ = counselor_person_user
        flag = _flag_from_observation(
            org,
            program,
            author_person,
            camper,
            (
                "Camper had a hard night, started crying after lights-out and "
                "is asking for parent contact. Watching closely."
            ),
        )
        _, user = cc_person_user
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get("/api/v1/camper-care/flags/", **_hdr(org.slug))
        assert r.status_code == 200
        items = r.json()["items"]
        row = next(item for item in items if item["id"] == str(flag.id))
        assert row["trigger_content_type"] == "specialist_note"
        assert row["trigger_preview"]
        assert "Camper had a hard night" in row["trigger_preview"]

    def test_preview_truncated_at_max_chars(
        self, api, org, program, cc_person_user, cc_membership,
        counselor_person_user, camper,
    ):
        author_person, _ = counselor_person_user
        very_long = "a" * 500
        _flag_from_observation(org, program, author_person, camper, very_long)
        _, user = cc_person_user
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get("/api/v1/camper-care/flags/", **_hdr(org.slug))
        body = r.json()
        snippet = body["items"][0]["trigger_preview"]
        assert snippet.endswith("\u2026")
        assert len(snippet) <= 161  # max 160 chars + ellipsis

    def test_missing_trigger_returns_empty_preview(
        self, api, org, program, cc_person_user, cc_membership, camper,
    ):
        """A flag with no resolvable trigger returns ``trigger_preview=""``."""
        Flag.all_objects.create(
            organization=org, program=program, subject_camper=camper,
            flagged_for_role="camper_care",
            trigger_content_type="", trigger_content_id="",
        )
        _, user = cc_person_user
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get("/api/v1/camper-care/flags/", **_hdr(org.slug))
        items = r.json()["items"]
        assert items[0]["trigger_preview"] == ""


class TestFlagDetail:
    def test_detail_returns_full_body_and_team_activity(
        self, api, org, program, cc_person_user, cc_membership,
        counselor_person_user, camper,
    ):
        """Expanding a flag returns the untruncated source note plus the
        audit history (every follow-up / resolve note the CC team wrote).
        """
        author_person, _ = counselor_person_user
        long_body = "Camper had a very hard night. " + ("detail " * 60)
        flag = _flag_from_observation(org, program, author_person, camper, long_body)
        _, user = cc_person_user
        api.force_authenticate(user=user)
        with organization_context(org):
            api.post(
                f"/api/v1/camper-care/flags/{flag.id}/follow-up/",
                {"note": "Checked in with the camper after dinner."},
                format="json", **_hdr(org.slug),
            )
            r = api.get(
                f"/api/v1/camper-care/flags/{flag.id}/", **_hdr(org.slug),
            )
        assert r.status_code == 200, r.content
        body = r.json()
        # Full (untruncated) source body, not the 160-char preview.
        assert body["trigger"]["body"] == long_body.strip()
        assert len(body["trigger"]["body"]) > 161
        # Team activity surfaces the follow-up note + its author.
        history = body["history"]
        assert any(
            row["reason_note"] == "Checked in with the camper after dinner."
            and row["after_state"].get("status") == "followed_up"
            for row in history
        )
        assert history[-1]["actor"]["membership_id"] == cc_membership.id

    def test_detail_404_for_unknown_flag(
        self, api, org, cc_person_user, cc_membership,
    ):
        _, user = cc_person_user
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get(
                f"/api/v1/camper-care/flags/{uuid4()}/", **_hdr(org.slug),
            )
        assert r.status_code == 404


class TestCamperDashboardFlagHistory:
    def test_flag_history_returned_newest_first(
        self, api, org, program, cc_person_user, cc_membership, cc_caseload,
        bunk, camper, camper_in_bunk,
    ):
        older = Flag.all_objects.create(
            organization=org, program=program, subject_camper=camper,
            flagged_for_role="camper_care", status=Flag.Status.RESOLVED,
            resolved_at=timezone.now(),
        )
        # Backdate older flag explicitly so ordering is deterministic.
        Flag.all_objects.filter(id=older.id).update(
            created_at=timezone.now() - timedelta(days=3),
        )
        newer = Flag.all_objects.create(
            organization=org, program=program, subject_camper=camper,
            flagged_for_role="camper_care", status=Flag.Status.ACTIVE,
        )
        _, user = cc_person_user
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get(
                f"/api/v1/camper-care/campers/{camper.id}/", **_hdr(org.slug),
            )
        assert r.status_code == 200, r.content
        history = r.json()["flag_history"]
        assert [row["id"] for row in history] == [str(newer.id), str(older.id)]
        # Resolved + Active should both surface so the arc is visible.
        statuses = {row["status"] for row in history}
        assert statuses == {Flag.Status.ACTIVE, Flag.Status.RESOLVED}
