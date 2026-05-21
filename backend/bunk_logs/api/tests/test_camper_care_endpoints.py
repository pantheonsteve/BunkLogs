"""Tests for ``/api/v1/camper-care/*`` (Step 7_8, Stories 18-23).

Coverage targets per lean mode:

* Happy + auth + critical edge per endpoint.
* Flag lifecycle (Active -> Followed Up -> Resolved -> Reopen) with
  audit trail.
* Order workspace team-shared visibility (CC7) -- every CC member in a
  program sees the same queue regardless of caseload.
* Camper Care note visibility regression -- Counselor and Unit Head
  cannot read non-sensitive CC notes (CC5).
* Specialist-note -> Flag helper creates an Active flag with audit.
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

from bunk_logs.core import flags as flag_helpers
from bunk_logs.core.context import organization_context
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import AuditEvent
from bunk_logs.core.models import Flag
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Note
from bunk_logs.core.models import Order
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
# Specialist note -> Flag helper (Step 7_8 scope item 2)
# ---------------------------------------------------------------------------


class TestRaiseFlagFromSpecialistNote:
    def test_creates_active_flag_with_trigger(
        self, org, program, camper, counselor_person_user,
    ):
        # Specialist note authored by anyone is fine; we just need a Note row.
        author_person, _ = counselor_person_user
        note = Note.all_objects.create(
            organization=org, program=program, subject=camper,
            author=author_person,
            note_type=Note.NoteType.SPECIALIST,
            body="needs follow-up",
            is_sensitive=False,
        )
        flag = flag_helpers.raise_flag_from_specialist_note(note)
        assert flag.status == Flag.Status.ACTIVE
        assert flag.trigger_content_type == "specialist_note"
        assert flag.trigger_content_id == str(note.id)
        assert flag.subject_camper_id == camper.id
        # Audit event written
        evts = AuditEvent.all_objects.filter(
            content_type="flag", content_id=str(flag.id),
            event_type=AuditEvent.EventType.CREATED,
        )
        assert evts.count() == 1


# ---------------------------------------------------------------------------
# Orders workspace -- team shared (CC7)
# ---------------------------------------------------------------------------


class TestCamperCareOrdersTeamShared:
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
# Camper Care notes -- visibility regression (CC5)
# ---------------------------------------------------------------------------


class TestCamperCareNotes:
    def test_create_note_happy_path(
        self, api, org, program, cc_person_user, cc_membership, camper,
    ):
        _, user = cc_person_user
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.post(
                "/api/v1/camper-care/notes/",
                {
                    "subject_id": camper.id,
                    "body": "Camper is settling in well.",
                    "category": "social",
                    "is_sensitive": False,
                },
                format="json", **_hdr(org.slug),
            )
        assert r.status_code == 201, r.content
        body = r.json()
        assert body["category"] == "social"
        assert body["note_type"] == "camper_care"

    def test_invalid_category_400(
        self, api, org, cc_person_user, cc_membership, camper,
    ):
        _, user = cc_person_user
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.post(
                "/api/v1/camper-care/notes/",
                {"subject_id": camper.id, "body": "x", "category": "bogus"},
                format="json", **_hdr(org.slug),
            )
        assert r.status_code == 400
        assert "category" in r.json()

    def test_edit_within_window_updates_and_audits(
        self, api, org, program, cc_person_user, cc_membership, camper,
    ):
        person, user = cc_person_user
        note = Note.all_objects.create(
            organization=org, program=program, subject=camper, author=person,
            note_type=Note.NoteType.CAMPER_CARE,
            body="initial", category="other",
        )
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.patch(
                f"/api/v1/camper-care/notes/{note.id}/",
                {"body": "updated"},
                format="json", **_hdr(org.slug),
            )
        assert r.status_code == 200, r.content
        note.refresh_from_db()
        assert note.body == "updated"
        assert AuditEvent.all_objects.filter(
            content_type="note", content_id=str(note.id),
            event_type=AuditEvent.EventType.EDITED,
        ).exists()

    def test_other_author_cannot_edit_within_window(
        self, api, org, program, cc_person_user, cc_membership,
        cc2_person_user, cc2_membership, camper,
    ):
        author, _ = cc_person_user
        note = Note.all_objects.create(
            organization=org, program=program, subject=camper, author=author,
            note_type=Note.NoteType.CAMPER_CARE,
            body="initial", category="other",
        )
        _, user2 = cc2_person_user
        api.force_authenticate(user=user2)
        with organization_context(org):
            r = api.patch(
                f"/api/v1/camper-care/notes/{note.id}/",
                {"body": "hostile edit"},
                format="json", **_hdr(org.slug),
            )
        assert r.status_code == 403  # criterion 7

    def test_edit_after_24h_window_403(
        self, api, org, program, cc_person_user, cc_membership, camper,
    ):
        author, user = cc_person_user
        old = timezone.now() - timedelta(hours=25)
        note = Note.all_objects.create(
            organization=org, program=program, subject=camper, author=author,
            note_type=Note.NoteType.CAMPER_CARE,
            body="old", category="other",
        )
        # Pin created_at to past via raw update so .save() doesn't refresh it.
        Note.all_objects.filter(pk=note.pk).update(created_at=old)
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.patch(
                f"/api/v1/camper-care/notes/{note.id}/",
                {"body": "should fail"},
                format="json", **_hdr(org.slug),
            )
        assert r.status_code == 403

    # ---- visibility regression: CC5 ------------------------------------

    def test_counselor_cannot_read_cc_note(
        self, api, org, program,
        cc_person_user, cc_membership,
        counselor_person_user, counselor_membership,
        camper,
    ):
        author, _ = cc_person_user
        Note.all_objects.create(
            organization=org, program=program, subject=camper, author=author,
            note_type=Note.NoteType.CAMPER_CARE,
            body="restricted to CC",
            is_sensitive=False,
            category="behavioral",
        )
        # We don't expose a generic Note list endpoint to counselors;
        # the regression check uses the visibility filter directly.
        from bunk_logs.core.filters import notes_visible_to

        _, co_user = counselor_person_user
        with organization_context(org):
            visible = notes_visible_to(co_user, Note.all_objects.all())
            assert visible.count() == 0  # CC5: counselor does not see CC notes

    def test_unit_head_cannot_read_cc_note(
        self, api, org, program,
        cc_person_user, cc_membership,
        uh_person_user, uh_membership,
        camper,
    ):
        author, _ = cc_person_user
        Note.all_objects.create(
            organization=org, program=program, subject=camper, author=author,
            note_type=Note.NoteType.CAMPER_CARE,
            body="restricted to CC",
            is_sensitive=False,
            category="behavioral",
        )
        from bunk_logs.core.filters import notes_visible_to

        _, uh_user = uh_person_user
        with organization_context(org):
            visible = notes_visible_to(uh_user, Note.all_objects.all())
            assert visible.count() == 0  # CC5: UH does not see CC notes

    def test_audience_disclosure_endpoint(
        self, api, org, cc_person_user, cc_membership,
    ):
        _, user = cc_person_user
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get(
                "/api/v1/camper-care/notes/audience/", **_hdr(org.slug),
            )
        assert r.status_code == 200
        body = r.json()
        assert body["is_sensitive"] is False
        # Default audience: CC + LT + Admin per CC5
        assert "Admin" in body["audience"]
        assert "Camper Care" in body["audience"]
        assert "Leadership Team" in body["audience"]
        assert "Health Center" not in body["audience"]
