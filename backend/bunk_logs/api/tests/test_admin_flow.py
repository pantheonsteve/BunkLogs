"""API tests for Step 7_13 PR1 -- Admin Flow dashboard / override / audit.

Covers:

* ``GET /api/v1/admin/dashboard/`` -- payload shape, attention cards,
  recent activity filter, auth gate.
* ``POST /api/v1/admin/override-edit/`` -- required-reason validation,
  before/after diff captured in audit, support for reflections and
  notes, cross-org isolation.
* ``GET /api/v1/admin/audit/`` -- meta-audit event written when the
  admin opens a content trail.
"""

from __future__ import annotations

from datetime import date
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from bunk_logs.core import audit as audit_module
from bunk_logs.core.context import organization_context
from bunk_logs.core.models import AuditEvent
from bunk_logs.core.models import Flag
from bunk_logs.core.models import MaintenanceTicket
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Note
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
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
    return Organization.objects.create(name="Admin Flow Org", slug="adminflow")


@pytest.fixture
def other_org():
    return Organization.objects.create(name="Other Admin Flow", slug="adminflow-other")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="Admin Flow Org Summer",
        slug="adminflow-summer",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def other_program(other_org):
    return Program.all_objects.create(
        organization=other_org,
        name="Other Admin Flow Summer",
        slug="other-adminflow-summer",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def admin_user(org, program):
    u = User.objects.create_user(email="admin@example.com", password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="Ada", last_name="Min", user=u,
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
    u = User.objects.create_user(email="counselor@example.com", password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="Carl", last_name="Counselor", user=u,
    )
    Membership.all_objects.create(
        program=program, person=person, role="counselor", is_active=True,
    )
    return u


@pytest.fixture
def cc_membership(org, program):
    person = Person.all_objects.create(
        organization=org, first_name="Cl", last_name="Care",
    )
    return Membership.all_objects.create(
        program=program, person=person, role="camper_care", is_active=True,
    )


@pytest.fixture
def subject(org):
    return Person.all_objects.create(
        organization=org, first_name="Sub", last_name="Ject",
    )


@pytest.fixture
def reflection_template(org):
    return ReflectionTemplate.all_objects.create(
        organization=org,
        program_type="summer_camp",
        role="counselor",
        name="Counselor self",
        slug="counselor-self",
        cadence="daily",
        schema={"fields": [{"key": "summary", "label": "Summary", "type": "long_text", "prompts": {"en": "How was today?"}}]},
        languages=["en"],
        subject_mode="self",
    )


@pytest.fixture
def reflection(org, program, reflection_template, subject):
    return Reflection.all_objects.create(
        organization=org,
        program=program,
        template=reflection_template,
        subject=subject,
        author=subject,
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 1),
        answers={"summary": "great day"},
        language="en",
        is_complete=True,
    )


@pytest.fixture
def note(org, program, subject, cc_membership):
    return Note.all_objects.create(
        organization=org,
        program=program,
        subject=subject,
        author=cc_membership.person,
        note_type=Note.NoteType.CAMPER_CARE,
        body="Subject needed a quiet break.",
        is_sensitive=False,
        category=Note.Category.SOCIAL,
    )


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


class TestAdminDashboard:
    def test_unauthenticated_blocked(self, api, org):
        r = api.get("/api/v1/admin/dashboard/", **_hdr(org.slug))
        assert r.status_code in (401, 403)

    def test_non_admin_blocked(self, api, org, non_admin_user):
        api.force_authenticate(user=non_admin_user)
        with organization_context(org):
            r = api.get("/api/v1/admin/dashboard/", **_hdr(org.slug))
        assert r.status_code == 403

    def test_admin_payload_shape(
        self, api, org, program, admin_user,
    ):
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.get("/api/v1/admin/dashboard/", **_hdr(org.slug))
        assert r.status_code == 200, r.content
        body = r.json()
        assert "today" in body
        assert body["org"]["slug"] == org.slug
        assert isinstance(body["org_snapshot"], dict)
        assert isinstance(body["attention_required"], list)
        # All six attention card keys present (zero counts allowed).
        keys = {c["key"] for c in body["attention_required"]}
        assert keys == {
            "stale_maintenance_tickets",
            "stale_camper_care_orders",
            "unresolved_flags",
            "pending_template_review",
            "digest_delivery_failures",
            "translation_pipeline_failures",
        }
        assert isinstance(body["recent_activity"], list)

    def test_active_people_count(
        self, api, org, program, admin_user, cc_membership,
    ):
        # cc_membership creates a second active person beyond the admin
        # fixture; ensure counts include both.
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.get("/api/v1/admin/dashboard/", **_hdr(org.slug))
        snapshot = r.json()["org_snapshot"]
        assert snapshot["active_people"] >= 2

    def test_attention_stale_maintenance_ticket_fires(
        self, api, org, program, admin_user,
    ):
        with organization_context(org):
            ticket = MaintenanceTicket.objects.create(
                organization=org, program=program,
                status=OrderStateMachine.NEW,
            )
            # Simulate the ticket being 10 days old (> default 3-day threshold).
            MaintenanceTicket.all_objects.filter(pk=ticket.pk).update(
                created_at=timezone.now() - timedelta(days=10),
            )
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.get("/api/v1/admin/dashboard/", **_hdr(org.slug))
        cards = {c["key"]: c["count"] for c in r.json()["attention_required"]}
        assert cards["stale_maintenance_tickets"] == 1

    def test_attention_unresolved_flag_fires(
        self, api, org, program, admin_user, subject, cc_membership,
    ):
        with organization_context(org):
            flag = Flag.objects.create(
                organization=org, program=program,
                subject_camper=subject,
                raised_by_membership=cc_membership,
                flagged_for_role="camper_care",
            )
            Flag.all_objects.filter(pk=flag.pk).update(
                created_at=timezone.now() - timedelta(days=10),
            )
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.get("/api/v1/admin/dashboard/", **_hdr(org.slug))
        cards = {c["key"]: c["count"] for c in r.json()["attention_required"]}
        assert cards["unresolved_flags"] == 1

    def test_recent_activity_excludes_routine_edits(
        self, api, org, program, admin_user, admin_membership, reflection,
    ):
        # A routine edit on a reflection should NOT show up in recent
        # activity (filtered out by content_type). An override on the
        # same reflection SHOULD show up.
        with organization_context(org):
            audit_module.edited(
                admin_membership, reflection,
                {"answers": {"summary": "a"}},
                {"answers": {"summary": "b"}},
            )
            audit_module.override_edit(
                admin_membership, reflection,
                {"answers": {"summary": "b"}},
                {"answers": {"summary": "c"}},
                reason="correction requested by family",
            )
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.get("/api/v1/admin/dashboard/", **_hdr(org.slug))
        activity = r.json()["recent_activity"]
        # Reflection edits/overrides are excluded -- the activity feed
        # focuses on operational events (orders, tickets, memberships,
        # supervisions, etc.).
        ev_types = {e["event_type"] for e in activity}
        # Routine "edited" reflection content_type isn't in ACTIVITY_CONTENT_FILTER
        # so neither event should appear.
        assert "edited" not in ev_types or all(
            e["content_type"] != "reflection" for e in activity
        )


# ---------------------------------------------------------------------------
# Override-edit
# ---------------------------------------------------------------------------


class TestAdminOverrideEdit:
    URL = "/api/v1/admin/override-edit/"

    def test_non_admin_blocked(self, api, org, non_admin_user, reflection):
        api.force_authenticate(user=non_admin_user)
        with organization_context(org):
            r = api.post(self.URL, {
                "content_type": "reflection",
                "content_id": str(reflection.id),
                "patch": {"answers": {"summary": "x"}},
                "reason": "rewrite",
            }, format="json", **_hdr(org.slug))
        assert r.status_code == 403

    def test_missing_reason_returns_422(self, api, org, admin_user, reflection):
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.post(self.URL, {
                "content_type": "reflection",
                "content_id": str(reflection.id),
                "patch": {"answers": {"summary": "x"}},
                "reason": "   ",
            }, format="json", **_hdr(org.slug))
        assert r.status_code == 422

    def test_missing_content_returns_400(self, api, org, admin_user):
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.post(self.URL, {
                "content_type": "",
                "content_id": "",
                "reason": "x",
            }, format="json", **_hdr(org.slug))
        assert r.status_code == 400

    def test_unsupported_content_type_returns_400(self, api, org, admin_user):
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.post(self.URL, {
                "content_type": "supervision",
                "content_id": "1",
                "patch": {},
                "reason": "x",
            }, format="json", **_hdr(org.slug))
        assert r.status_code == 400

    def test_reflection_override_writes_audit_with_before_after(
        self, api, org, admin_user, reflection,
    ):
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.post(self.URL, {
                "content_type": "reflection",
                "content_id": str(reflection.id),
                "patch": {"answers": {"summary": "rewritten by admin"}},
                "reason": "Camper asked to remove identifying detail",
            }, format="json", **_hdr(org.slug))
        assert r.status_code == 200, r.content
        body = r.json()
        assert body["before"]["answers"] == {"summary": "great day"}
        assert body["after"]["answers"] == {"summary": "rewritten by admin"}
        # AuditEvent is recorded with is_admin_override=True
        evts = AuditEvent.all_objects.filter(
            content_type="reflection",
            content_id=str(reflection.id),
            event_type=AuditEvent.EventType.OVERRIDE_EDIT,
        )
        assert evts.count() == 1
        evt = evts.first()
        assert evt.is_admin_override is True
        assert evt.reason_note == "Camper asked to remove identifying detail"
        assert evt.before_state["answers"] == {"summary": "great day"}
        assert evt.after_state["answers"] == {"summary": "rewritten by admin"}

    def test_note_override_updates_body(self, api, org, admin_user, note):
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.post(self.URL, {
                "content_type": "note",
                "content_id": str(note.id),
                "patch": {"body": "Redacted by Admin"},
                "reason": "Reviewed for sensitive identifiers",
            }, format="json", **_hdr(org.slug))
        assert r.status_code == 200, r.content
        note.refresh_from_db()
        assert note.body == "Redacted by Admin"
        assert AuditEvent.all_objects.filter(
            content_type="note",
            content_id=str(note.id),
            event_type=AuditEvent.EventType.OVERRIDE_EDIT,
        ).exists()

    def test_cross_org_target_returns_404(
        self, api, org, other_org, other_program, admin_user,
    ):
        # Reflection in another org should not be reachable.
        with organization_context(other_org):
            tpl = ReflectionTemplate.all_objects.create(
                organization=other_org,
                program_type="summer_camp",
                role="counselor",
                name="Other tpl",
                slug="other-tpl",
                cadence="daily",
                schema={"fields": [{"key": "k", "label": "K", "type": "long_text", "prompts": {"en": "?"}}]},
                languages=["en"],
                subject_mode="self",
            )
            person = Person.all_objects.create(
                organization=other_org, first_name="A", last_name="B",
            )
            other_ref = Reflection.all_objects.create(
                organization=other_org, program=other_program, template=tpl,
                subject=person, author=person,
                period_start=date(2026, 7, 1), period_end=date(2026, 7, 1),
                answers={"k": "v"}, is_complete=True,
            )
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.post(self.URL, {
                "content_type": "reflection",
                "content_id": str(other_ref.id),
                "patch": {"answers": {"k": "v2"}},
                "reason": "no",
            }, format="json", **_hdr(org.slug))
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Admin audit pass-through
# ---------------------------------------------------------------------------


class TestAdminAuditPassthrough:
    def test_meta_audit_written_via_admin_path(
        self, api, org, admin_user, admin_membership, reflection,
    ):
        with organization_context(org):
            audit_module.created(admin_membership, reflection)
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.get(
                "/api/v1/admin/audit/",
                {"content_type": "reflection", "content_id": str(reflection.id)},
                **_hdr(org.slug),
            )
        assert r.status_code == 200
        view_events = AuditEvent.all_objects.filter(
            event_type=AuditEvent.EventType.AUDIT_VIEW,
            content_type="reflection",
            content_id=str(reflection.id),
        )
        assert view_events.count() == 1

    def test_admin_overrides_listing(
        self, api, org, admin_user, admin_membership, reflection,
    ):
        with organization_context(org):
            audit_module.override_edit(
                admin_membership, reflection,
                {"answers": {"summary": "a"}},
                {"answers": {"summary": "b"}},
                reason="cleanup",
            )
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.get(
                "/api/v1/admin/audit/admin-overrides/",
                **_hdr(org.slug),
            )
        assert r.status_code == 200
        body = r.json()
        assert any(e["event_type"] == "override_edit" for e in body)
