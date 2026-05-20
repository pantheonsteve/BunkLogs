"""API tests for Step 7_5 i18n surfaces.

Covers:

* ``GET / PATCH /api/v1/me/preferences/`` -- including the 404 path for
  users that don't yet have a ``Person`` row.
* ``POST /api/v1/reflections/<id>/retry-translation/`` -- happy path,
  English short-circuit, gating on current TranslationRecord status.
* Translation embed shape on the Reflection serializer.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import TranslationRecord

User = get_user_model()


MINIMAL_SCHEMA = {
    "fields": [
        {"key": "highlights", "type": "textarea", "label": {"en": "Highlights", "es": "Logros"}},
    ],
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def org():
    return Organization.objects.create(name="i18n Org", slug="i18n-org")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="i18n Org Summer 2026",
        slug="i18n-summer",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
        is_active=True,
    )


@pytest.fixture
def template(org):
    return ReflectionTemplate.all_objects.create(
        organization=org,
        name="i18n Daily",
        slug="i18n-daily",
        cadence="daily",
        role="counselor",
        program_type="summer_camp",
        schema=MINIMAL_SCHEMA,
        languages=["en", "es"],
        is_active=True,
    )


@pytest.fixture
def user_with_person(org, program):
    u = User.objects.create_user(email="counselor@example.com", password="pw")
    p = Person.all_objects.create(
        organization=org, first_name="C", last_name="One", user=u,
        preferred_language="en",
    )
    Membership.all_objects.create(
        program=program, person=p, role="counselor", is_active=True,
    )
    return u, p


@pytest.fixture
def user_without_person():
    return User.objects.create_user(email="orphan@example.com", password="pw")


@pytest.fixture
def admin_user(org, program):
    u = User.objects.create_user(email="adm@example.com", password="pw")
    p = Person.all_objects.create(
        organization=org, first_name="A", last_name="D", user=u,
    )
    Membership.all_objects.create(
        program=program, person=p, role="admin", is_active=True,
    )
    return u, p


def _hdr_org(slug: str):
    return {"HTTP_X_ORGANIZATION_SLUG": slug}


# ---------------------------------------------------------------------------
# /api/v1/me/preferences/
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMePreferencesEndpoint:
    URL = "/api/v1/me/preferences/"

    def test_get_returns_defaults(self, api, user_with_person):
        user, _ = user_with_person
        api.force_authenticate(user=user)
        resp = api.get(self.URL)
        assert resp.status_code == 200, resp.content
        body = resp.json()
        assert body["preferred_language"] == "en"
        assert body["translation_preference"] == "translation_first"

    def test_get_requires_authentication(self, api):
        assert api.get(self.URL).status_code in (401, 403)

    def test_patch_updates_preferred_language(self, api, user_with_person):
        user, person = user_with_person
        api.force_authenticate(user=user)
        resp = api.patch(self.URL, {"preferred_language": "es"}, format="json")
        assert resp.status_code == 200, resp.content
        assert resp.json()["preferred_language"] == "es"
        person.refresh_from_db()
        assert person.preferred_language == "es"

    def test_patch_updates_translation_preference(self, api, user_with_person):
        user, person = user_with_person
        api.force_authenticate(user=user)
        resp = api.patch(
            self.URL, {"translation_preference": "original_first"}, format="json",
        )
        assert resp.status_code == 200, resp.content
        person.refresh_from_db()
        assert person.translation_preference == "original_first"

    def test_patch_rejects_unsupported_language(self, api, user_with_person):
        user, _ = user_with_person
        api.force_authenticate(user=user)
        resp = api.patch(self.URL, {"preferred_language": "fr"}, format="json")
        assert resp.status_code == 400, resp.content

    def test_patch_ignores_extra_fields(self, api, user_with_person):
        # Defensive: the serializer must NOT let unrelated Person fields
        # ride along on a preferences PATCH.
        user, person = user_with_person
        api.force_authenticate(user=user)
        before_first = person.first_name
        resp = api.patch(
            self.URL,
            {"preferred_language": "en", "first_name": "Hijacked"},
            format="json",
        )
        assert resp.status_code == 200, resp.content
        person.refresh_from_db()
        assert person.first_name == before_first

    def test_orphan_user_gets_404(self, api, user_without_person):
        api.force_authenticate(user=user_without_person)
        assert api.get(self.URL).status_code == 404
        assert api.patch(self.URL, {"preferred_language": "en"}, format="json").status_code == 404


# ---------------------------------------------------------------------------
# Reflection retry-translation endpoint
# ---------------------------------------------------------------------------


def _reflection(org, program, template, person, *, language="es"):
    # ``submitted_by`` is a FK to ``settings.AUTH_USER_MODEL`` and nullable.
    # The translation embed + retry endpoint don't read it, so we omit it
    # here -- callers that need the user can use ``person.user`` directly.
    return Reflection.all_objects.create(
        organization=org,
        program=program,
        template=template,
        subject=person,
        author=person,
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 7),
        answers={"highlights": "Hoy."},
        language=language,
    )


@pytest.mark.django_db
class TestReflectionTranslationEmbedAndRetry:
    def test_english_reflection_has_null_translation_embed(
        self, api, org, program, template, user_with_person,
    ):
        user, person = user_with_person
        ref = _reflection(org, program, template, person, language="en")
        api.force_authenticate(user=user)
        resp = api.get(f"/api/v1/reflections/{ref.pk}/", **_hdr_org(org.slug))
        assert resp.status_code == 200, resp.content
        assert resp.json()["translation"] is None

    def test_non_english_reflection_embeds_pending_state(
        self, api, org, program, template, user_with_person,
    ):
        user, person = user_with_person
        ref = _reflection(org, program, template, person, language="es")
        api.force_authenticate(user=user)
        resp = api.get(f"/api/v1/reflections/{ref.pk}/", **_hdr_org(org.slug))
        assert resp.status_code == 200, resp.content
        translation = resp.json()["translation"]
        assert translation["status"] == "pending"
        assert translation["source_language"] == "es"
        assert translation["target_language"] == "en"

    def test_retry_translation_only_allowed_for_failed_states(
        self, api, org, program, template, user_with_person,
    ):
        user, person = user_with_person
        ref = _reflection(org, program, template, person, language="es")
        TranslationRecord.all_objects.create(
            organization=org,
            content_type="reflection",
            content_id=str(ref.pk),
            source_language="es",
            target_language="en",
            status=TranslationRecord.Status.PENDING,
        )
        api.force_authenticate(user=user)
        resp = api.post(
            f"/api/v1/reflections/{ref.pk}/retry-translation/", **_hdr_org(org.slug),
        )
        assert resp.status_code == 409, resp.content

    def test_retry_translation_resets_attempts_and_enqueues(
        self, api, org, program, template, user_with_person,
    ):
        user, person = user_with_person
        ref = _reflection(org, program, template, person, language="es")
        record = TranslationRecord.all_objects.create(
            organization=org,
            content_type="reflection",
            content_id=str(ref.pk),
            source_language="es",
            target_language="en",
            status=TranslationRecord.Status.FAILED_RETRYABLE,
            attempt_count=3,
            last_error="boom",
        )
        api.force_authenticate(user=user)
        with patch(
            "bunk_logs.api.reflections.enqueue_translation_for_reflection",
        ) as fake_enqueue:
            resp = api.post(
                f"/api/v1/reflections/{ref.pk}/retry-translation/",
                **_hdr_org(org.slug),
            )
        assert resp.status_code == 202, resp.content
        fake_enqueue.assert_called_once()
        record.refresh_from_db()
        assert record.status == TranslationRecord.Status.PENDING
        assert record.attempt_count == 0
        assert record.last_error == ""

    def test_retry_translation_rejects_english_reflections(
        self, api, org, program, template, user_with_person,
    ):
        user, person = user_with_person
        ref = _reflection(org, program, template, person, language="en")
        api.force_authenticate(user=user)
        resp = api.post(
            f"/api/v1/reflections/{ref.pk}/retry-translation/", **_hdr_org(org.slug),
        )
        assert resp.status_code == 400, resp.content
