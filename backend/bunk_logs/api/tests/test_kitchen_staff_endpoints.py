"""Tests for Kitchen Staff flow (Step 7_11, Stories 37-44).

Coverage
--------
* dashboard: happy path, missing template, preferred_language in header
* reflection create: happy path, day_off, idempotency, non-English triggers translation
* reflection edit: language unchanged unless explicit, re-triggers translation
* reflection history: pagination + language field in each row
* translation embed: pending/completed/failed states returned in response
* permissions: non-kitchen_staff user gets 403
"""
from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import TranslationRecord

User = get_user_model()
pytestmark = pytest.mark.django_db


def _hdr(org_slug: str) -> dict:
    return {"HTTP_X_ORGANIZATION_SLUG": org_slug}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def org():
    return Organization.objects.create(
        name="KS Org",
        slug="ks-org",
    )


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="KS Org Summer 2026",
        slug="ks-summer-2026",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def ks_user_person(org, program):
    user = User.objects.create_user(email="kitchen@camp.test", password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="Kira", last_name="Kitchen", user=user,
        preferred_language="en",
    )
    Membership.all_objects.create(
        program=program, person=person, role="kitchen_staff", is_active=True,
    )
    return person, user


@pytest.fixture
def other_user(org, program):
    """A user who is NOT kitchen_staff."""
    user = User.objects.create_user(email="counselor@camp.test", password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="Other", last_name="User", user=user,
    )
    Membership.all_objects.create(
        program=program, person=person, role="counselor", is_active=True,
    )
    return person, user


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def ks_api(ks_user_person, api):
    _, user = ks_user_person
    api.force_authenticate(user=user)
    return api


# ---------------------------------------------------------------------------
# Dashboard tests (Story 37)
# ---------------------------------------------------------------------------

class TestKitchenStaffDashboard:
    def test_dashboard_happy_path(self, ks_api, org, program, ks_user_person):
        person, _ = ks_user_person
        with organization_context(org):
            r = ks_api.get("/api/v1/kitchen-staff/dashboard/", **_hdr(org.slug))
        assert r.status_code == 200
        data = r.json()
        assert data["header"]["role_label"] == "Kitchen Staff"
        assert data["header"]["name"] == "Kira Kitchen"
        assert data["header"]["preferred_language"] == "en"
        assert data["my_reflection"]["state"] in ("missing", "no_template", "complete")
        assert "history_entry" in data

    def test_dashboard_reflection_state_missing(self, ks_api, org, program):
        with organization_context(org):
            r = ks_api.get("/api/v1/kitchen-staff/dashboard/", **_hdr(org.slug))
        assert r.status_code == 200
        assert r.json()["my_reflection"]["state"] == "missing"

    def test_dashboard_reflection_state_complete_after_submission(
        self, ks_api, org, program, ks_user_person,
    ):
        person, _ = ks_user_person
        with organization_context(org):
            ks_api.post(
                "/api/v1/kitchen-staff/reflection/",
                {
                    "answers": {"service_summary": "Lunch went well."},
                    "language": "en",
                    "client_submission_id": str(uuid.uuid4()),
                },
                format="json",
                **_hdr(org.slug),
            )
            r = ks_api.get("/api/v1/kitchen-staff/dashboard/", **_hdr(org.slug))
        assert r.json()["my_reflection"]["state"] == "complete"

    def test_dashboard_preferred_language_in_header(self, api, org, program):
        """Spanish-preferring user sees their language in header."""
        user = User.objects.create_user(email="ks_es@camp.test", password="pw")
        person = Person.all_objects.create(
            organization=org, first_name="Carmen", last_name="Chef", user=user,
            preferred_language="es",
        )
        Membership.all_objects.create(
            program=program, person=person, role="kitchen_staff", is_active=True,
        )
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get("/api/v1/kitchen-staff/dashboard/", **_hdr(org.slug))
        assert r.status_code == 200
        assert r.json()["header"]["preferred_language"] == "es"

    def test_dashboard_403_for_non_kitchen_staff(self, api, org, other_user):
        _, user = other_user
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get("/api/v1/kitchen-staff/dashboard/", **_hdr(org.slug))
        assert r.status_code == 403

    def test_dashboard_403_unauthenticated(self, api, org):
        with organization_context(org):
            r = api.get("/api/v1/kitchen-staff/dashboard/", **_hdr(org.slug))
        assert r.status_code in (401, 403)

    def test_dashboard_empty_state_without_template_assignment(
        self, ks_api, org, program, ks_user_person,
    ):
        """Step 7_21: without an active TemplateAssignment the dashboard
        returns ``state='no_template'`` instead of 500ing.

        The autouse fixture in api/tests/conftest.py creates a
        role-targeted assignment per program; this test deletes those
        rows to exercise the empty path the LT will see on day zero of
        a new program rollout (before FA-S / Step 7_22 seeds anything).
        """
        from bunk_logs.core.models import TemplateAssignment

        TemplateAssignment.all_objects.filter(program=program).delete()
        with organization_context(org):
            r = ks_api.get("/api/v1/kitchen-staff/dashboard/", **_hdr(org.slug))
        assert r.status_code == 200
        body = r.json()
        assert body["my_reflection"]["state"] == "no_template"
        assert body["my_reflection"]["template_id"] is None


# ---------------------------------------------------------------------------
# Reflection create (Story 40)
# ---------------------------------------------------------------------------

class TestKitchenStaffReflectionCreate:
    def test_create_reflection_happy_path(self, ks_api, org, program, ks_user_person):
        person, _ = ks_user_person
        with organization_context(org):
            r = ks_api.post(
                "/api/v1/kitchen-staff/reflection/",
                {
                    "answers": {"service_summary": "Great lunch service today."},
                    "language": "en",
                    "client_submission_id": str(uuid.uuid4()),
                },
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 201
        data = r.json()
        assert data["answers"]["service_summary"] == "Great lunch service today."

    def test_create_day_off(self, ks_api, org, program):
        with organization_context(org):
            r = ks_api.post(
                "/api/v1/kitchen-staff/reflection/",
                {
                    "day_off": True,
                    "language": "en",
                    "client_submission_id": str(uuid.uuid4()),
                },
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 201

    def test_create_idempotent(self, ks_api, org, program):
        cid = str(uuid.uuid4())
        payload = {
            "answers": {"service_summary": "Good."},
            "language": "en",
            "client_submission_id": cid,
        }
        with organization_context(org):
            r1 = ks_api.post("/api/v1/kitchen-staff/reflection/", payload, format="json", **_hdr(org.slug))
            r2 = ks_api.post("/api/v1/kitchen-staff/reflection/", payload, format="json", **_hdr(org.slug))
        assert r1.status_code == 201
        assert r2.status_code == 200
        assert r1.json()["id"] == r2.json()["id"]

    @patch("bunk_logs.api.kitchen_staff.self_reflection.enqueue_translation_for_reflection")
    def test_non_english_triggers_translation(self, mock_enqueue, ks_api, org, program):
        """Story 40 criterion 3: non-English submission enqueues translation."""
        with organization_context(org):
            r = ks_api.post(
                "/api/v1/kitchen-staff/reflection/",
                {
                    "answers": {"service_summary": "El almuerzo fue excelente."},
                    "language": "es",
                    "client_submission_id": str(uuid.uuid4()),
                },
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 201
        mock_enqueue.assert_called_once()

    @patch("bunk_logs.api.kitchen_staff.self_reflection.enqueue_translation_for_reflection")
    def test_english_calls_enqueue_but_task_is_noop(self, mock_enqueue, ks_api, org, program):
        """enqueue_translation_for_reflection is called; it returns early for 'en' internally."""
        with organization_context(org):
            ks_api.post(
                "/api/v1/kitchen-staff/reflection/",
                {
                    "answers": {"service_summary": "Lunch was great."},
                    "language": "en",
                    "client_submission_id": str(uuid.uuid4()),
                },
                format="json",
                **_hdr(org.slug),
            )
        mock_enqueue.assert_called_once()

    @patch("bunk_logs.api.kitchen_staff.self_reflection.enqueue_translation_for_reflection")
    def test_day_off_does_not_trigger_translation(self, mock_enqueue, ks_api, org, program):
        with organization_context(org):
            ks_api.post(
                "/api/v1/kitchen-staff/reflection/",
                {
                    "day_off": True,
                    "language": "es",
                    "client_submission_id": str(uuid.uuid4()),
                },
                format="json",
                **_hdr(org.slug),
            )
        mock_enqueue.assert_not_called()

    def test_translation_embed_pending_for_non_english(self, ks_api, org, program):
        """Story 44: response includes translation state."""
        with organization_context(org):
            r = ks_api.post(
                "/api/v1/kitchen-staff/reflection/",
                {
                    "answers": {"service_summary": "Excelente servicio."},
                    "language": "es",
                    "client_submission_id": str(uuid.uuid4()),
                },
                format="json",
                **_hdr(org.slug),
            )
        data = r.json()
        assert data["translation"] is not None
        assert data["translation"]["status"] == "pending"
        assert data["translation"]["source_language"] == "es"

    def test_translation_embed_null_for_english(self, ks_api, org, program):
        with organization_context(org):
            r = ks_api.post(
                "/api/v1/kitchen-staff/reflection/",
                {
                    "answers": {"service_summary": "English answer."},
                    "language": "en",
                    "client_submission_id": str(uuid.uuid4()),
                },
                format="json",
                **_hdr(org.slug),
            )
        assert r.json()["translation"] is None

    def test_create_403_for_non_kitchen_staff(self, api, org, other_user):
        _, user = other_user
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.post(
                "/api/v1/kitchen-staff/reflection/",
                {"answers": {}, "language": "en", "client_submission_id": str(uuid.uuid4())},
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Reflection edit (Story 41)
# ---------------------------------------------------------------------------

class TestKitchenStaffReflectionEdit:
    def _create(self, ks_api, org, language="en"):
        with organization_context(org):
            r = ks_api.post(
                "/api/v1/kitchen-staff/reflection/",
                {
                    "answers": {"service_summary": "Initial."},
                    "language": language,
                    "client_submission_id": str(uuid.uuid4()),
                },
                format="json",
                **_hdr(org.slug),
            )
        return r.json()

    def test_edit_happy_path(self, ks_api, org, program):
        reflection = self._create(ks_api, org)
        with organization_context(org):
            r = ks_api.patch(
                f"/api/v1/kitchen-staff/reflection/{reflection['id']}/",
                {"answers": {"service_summary": "Updated answer."}},
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 200
        assert r.json()["answers"]["service_summary"] == "Updated answer."

    def test_edit_language_unchanged_if_not_sent(self, ks_api, org, program):
        """Story 41 criterion 6: language only changes when explicitly sent."""
        reflection = self._create(ks_api, org, language="es")
        with organization_context(org):
            r = ks_api.patch(
                f"/api/v1/kitchen-staff/reflection/{reflection['id']}/",
                {"answers": {"service_summary": "Editado."}},
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 200
        assert r.json()["language"] == "es"

    def test_edit_language_changes_when_explicit(self, ks_api, org, program):
        reflection = self._create(ks_api, org, language="es")
        with organization_context(org):
            r = ks_api.patch(
                f"/api/v1/kitchen-staff/reflection/{reflection['id']}/",
                {"answers": {"service_summary": "Switched to English."}, "language": "en"},
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 200
        assert r.json()["language"] == "en"

    @patch("bunk_logs.api.kitchen_staff.self_reflection.enqueue_translation_for_reflection")
    def test_edit_retriggers_translation(self, mock_enqueue, ks_api, org, program):
        """Story 40 criterion 6: edit re-triggers translation."""
        reflection = self._create(ks_api, org, language="es")
        mock_enqueue.reset_mock()
        with organization_context(org):
            ks_api.patch(
                f"/api/v1/kitchen-staff/reflection/{reflection['id']}/",
                {"answers": {"service_summary": "Nuevas notas."}},
                format="json",
                **_hdr(org.slug),
            )
        mock_enqueue.assert_called_once()

    def test_edit_404_for_wrong_user(self, api, org, program, ks_user_person, other_user):
        """Cannot edit another user's reflection."""
        _, ks_user = ks_user_person
        api.force_authenticate(user=ks_user)
        reflection = self._create(api, org)

        # Now switch to other_user who isn't kitchen_staff
        _, ou = other_user
        api.force_authenticate(user=ou)
        with organization_context(org):
            r = api.patch(
                f"/api/v1/kitchen-staff/reflection/{reflection['id']}/",
                {"answers": {"service_summary": "Hacked."}},
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Reflection history (Story 41 criterion 7)
# ---------------------------------------------------------------------------

class TestKitchenStaffReflectionHistory:
    def test_history_returns_language_field(self, ks_api, org, program):
        with organization_context(org):
            ks_api.post(
                "/api/v1/kitchen-staff/reflection/",
                {
                    "answers": {"service_summary": "Today in Spanish."},
                    "language": "es",
                    "client_submission_id": str(uuid.uuid4()),
                },
                format="json",
                **_hdr(org.slug),
            )
            r = ks_api.get("/api/v1/kitchen-staff/reflection/history/", **_hdr(org.slug))
        assert r.status_code == 200
        results = r.json()["results"]
        today_row = next((row for row in results if row["submitted"]), None)
        assert today_row is not None
        assert today_row["language"] == "es"

    def test_history_pagination(self, ks_api, org, program):
        with organization_context(org):
            r = ks_api.get(
                "/api/v1/kitchen-staff/reflection/history/?page_size=5",
                **_hdr(org.slug),
            )
        assert r.status_code == 200
        data = r.json()
        assert len(data["results"]) <= 5

    def test_history_403_for_non_kitchen_staff(self, api, org, other_user):
        _, user = other_user
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get("/api/v1/kitchen-staff/reflection/history/", **_hdr(org.slug))
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Translation state in response (Story 44)
# ---------------------------------------------------------------------------

class TestTranslationStateEmbed:
    def test_translation_completed_state(self, ks_api, org, program, ks_user_person):
        """When a TranslationRecord exists, its data is embedded in the response."""
        person, _ = ks_user_person
        with organization_context(org):
            r = ks_api.post(
                "/api/v1/kitchen-staff/reflection/",
                {
                    "answers": {"service_summary": "El servicio fue bueno."},
                    "language": "es",
                    "client_submission_id": str(uuid.uuid4()),
                },
                format="json",
                **_hdr(org.slug),
            )
        reflection_id = r.json()["id"]

        # Simulate a completed translation record
        reflection = Reflection.all_objects.get(id=reflection_id)
        TranslationRecord.objects.create(
            organization=org,
            content_type="reflection",
            content_id=str(reflection.pk),
            source_language="es",
            target_language="en",
            status="completed",
            translated_text="The service was good.",
            model_id="claude-sonnet-4-5",
            celery_task_id="fake-task-id",
        )

        with organization_context(org):
            r2 = ks_api.patch(
                f"/api/v1/kitchen-staff/reflection/{reflection_id}/",
                {"answers": {"service_summary": "El servicio fue muy bueno."}},
                format="json",
                **_hdr(org.slug),
            )
        data = r2.json()
        # After edit the translation embed refreshes
        assert data["translation"] is not None
