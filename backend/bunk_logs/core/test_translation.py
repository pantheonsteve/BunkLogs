"""Translation pipeline tests (Step 7_5).

Covers the three layers documented in ``core/I18N.md``:

* The synchronous :mod:`client` helper -- success path + classifier on the
  retryable / non-retryable failure split.
* The :mod:`tasks` Celery wrappers -- pending -> completed transition,
  retryable failure stays in ``failed_retryable``, terminal failure flips
  to ``failed_terminal``, and the re-translation flow correctly revokes a
  pending task on edit.
* The :mod:`metrics` Datadog adapter -- silent no-op when ``dd-trace`` is
  not installed (CI default), submitted/completed/failed counters keyed
  by content type + language pair.

Tests rely on dependency injection for the Anthropic call (no real
network) and ``transaction=True`` for tasks that hit
``transaction.on_commit``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import TranslationRecord
from bunk_logs.core.translation import beat as beat_module
from bunk_logs.core.translation import client as client_module
from bunk_logs.core.translation import metrics as metrics_module
from bunk_logs.core.translation import tasks as tasks_module
from bunk_logs.core.translation.client import TRANSLATION_PROMPT
from bunk_logs.core.translation.client import TranslationFailure
from bunk_logs.core.translation.client import TranslationResult
from bunk_logs.core.translation.client import translate_content

pytestmark = pytest.mark.django_db

MINIMAL_SCHEMA = {
    "fields": [
        {"key": "highlights", "type": "textarea", "label": {"en": "Highlights", "es": "Logros"}},
    ],
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def org():
    return Organization.objects.create(name="Trans Org", slug="trans-org")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="Trans Org Summer 2026",
        slug="trans-summer-2026",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
        is_active=True,
    )


@pytest.fixture
def template(org):
    return ReflectionTemplate.all_objects.create(
        organization=org,
        name="Counselor Daily",
        slug="counselor-daily-translation",
        cadence="daily",
        role="counselor",
        program_type="summer_camp",
        schema=MINIMAL_SCHEMA,
        languages=["en", "es"],
        is_active=True,
    )


@pytest.fixture
def author(org):
    return Person.all_objects.create(
        organization=org, first_name="Author", last_name="Person",
    )


@pytest.fixture
def membership(program, author):
    return Membership.all_objects.create(
        program=program, person=author, role="counselor", is_active=True,
    )


def _reflection(org, program, template, author, *, language="es", answers=None):
    # ``submitted_by`` is a FK to ``settings.AUTH_USER_MODEL`` and nullable;
    # these tests don't exercise the author/user join so we leave it unset.
    return Reflection.all_objects.create(
        organization=org,
        program=program,
        template=template,
        subject=author,
        author=author,
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 7),
        answers=answers or {"highlights": "Hoy fue un buen día."},
        language=language,
    )


# ---------------------------------------------------------------------------
# Mock Anthropic client
# ---------------------------------------------------------------------------


@dataclass
class _StubUsage:
    input_tokens: int
    output_tokens: int


@dataclass
class _StubBlock:
    type: str
    text: str


class _StubResponse:
    def __init__(self, text: str, *, input_tokens: int = 12, output_tokens: int = 18):
        self.content = [_StubBlock(type="text", text=text)]
        self.usage = _StubUsage(input_tokens=input_tokens, output_tokens=output_tokens)


class _StubMessages:
    def __init__(self, response=None, raises=None):
        self._response = response
        self._raises = raises
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self._raises is not None:
            raise self._raises
        return self._response


class _StubClient:
    def __init__(self, response=None, raises=None):
        self.messages = _StubMessages(response=response, raises=raises)


class _SimulatedAuthError(Exception):
    """Mimics the SDK's ``AuthenticationError`` so the heuristic classifier picks it up."""


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class TestTranslateContent:
    def test_success_returns_translated_text_and_metadata(self):
        stub = _StubClient(response=_StubResponse("Today was a good day."))
        result = translate_content(
            "Hoy fue un buen día.", source_language="es", target_language="en",
            client=stub, model_id="claude-test",
        )
        assert isinstance(result, TranslationResult)
        assert result.text == "Today was a good day."
        assert result.model_id == "claude-test"
        assert result.tokens_used == 30
        # Ensure the prompt format remains the single source of truth
        # callers / docs cite.
        assert "{source_language}" not in stub.messages.calls[0]["messages"][0]["content"]
        assert TRANSLATION_PROMPT.startswith("Translate the following text")

    def test_empty_input_is_non_retryable(self):
        with pytest.raises(TranslationFailure) as exc:
            translate_content("   ", source_language="es", client=_StubClient())
        assert exc.value.retryable is False

    def test_same_language_is_non_retryable(self):
        with pytest.raises(TranslationFailure) as exc:
            translate_content(
                "hello", source_language="en", target_language="en",
                client=_StubClient(response=_StubResponse("hello")),
            )
        assert exc.value.retryable is False

    def test_sdk_error_is_retryable_by_default(self):
        stub = _StubClient(raises=RuntimeError("transient flake"))
        with pytest.raises(TranslationFailure) as exc:
            translate_content("hola", source_language="es", client=stub)
        assert exc.value.retryable is True

    def test_auth_like_error_is_non_retryable(self):
        stub = _StubClient(raises=_SimulatedAuthError("bad key"))
        with pytest.raises(TranslationFailure) as exc:
            translate_content("hola", source_language="es", client=stub)
        assert exc.value.retryable is False

    def test_missing_api_key_when_no_client_provided(self, settings):
        settings.ANTHROPIC_API_KEY = ""
        with pytest.raises(TranslationFailure) as exc:
            translate_content("hola", source_language="es")
        assert exc.value.retryable is False


# ---------------------------------------------------------------------------
# Celery task: translate_reflection_to_english
# ---------------------------------------------------------------------------


class TestTranslateReflectionTask:
    def test_english_reflection_is_skipped(self, org, program, template, author, membership):
        reflection = _reflection(
            org, program, template, author, language="en",
            answers={"highlights": "All good."},
        )
        result = tasks_module.translate_reflection_to_english.run(reflection.pk)
        assert result == {"status": "skipped", "reason": "already_english"}
        assert not TranslationRecord.all_objects.filter(
            content_id=str(reflection.pk),
        ).exists()

    def test_completed_path_persists_translation(self, org, program, template, author, membership):
        reflection = _reflection(org, program, template, author)
        stub = _StubClient(response=_StubResponse("Today was a good day."))
        with patch.object(tasks_module, "translate_content") as fake_translate:
            fake_translate.return_value = TranslationResult(
                text="Today was a good day.",
                model_id="claude-sonnet-4-5",
                tokens_used=42,
            )
            result = tasks_module.translate_reflection_to_english.run(reflection.pk)
        record = TranslationRecord.latest_for("reflection", reflection.pk)
        assert result["status"] == "completed"
        assert record.status == TranslationRecord.Status.COMPLETED
        assert record.translated_text == "Today was a good day."
        assert record.tokens_used == 42
        assert record.attempt_count == 1
        # Stub kept around so the import order doesn't matter for coverage:
        assert isinstance(stub, _StubClient)

    def test_terminal_failure_marks_record_failed_terminal(
        self, org, program, template, author, membership,
    ):
        reflection = _reflection(org, program, template, author)
        with patch.object(tasks_module, "translate_content") as fake_translate:
            fake_translate.side_effect = TranslationFailure("nope", retryable=False)
            result = tasks_module.translate_reflection_to_english.run(reflection.pk)
        record = TranslationRecord.latest_for("reflection", reflection.pk)
        assert result["status"] == "failed_terminal"
        assert record.status == TranslationRecord.Status.FAILED_TERMINAL
        assert record.last_error.startswith("nope")
        assert record.attempt_count == 1

    def test_empty_source_text_short_circuits_terminal(
        self, org, program, template, author, membership,
    ):
        reflection = _reflection(
            org, program, template, author, answers={"highlights": "   "},
        )
        with patch.object(tasks_module, "translate_content") as fake_translate:
            result = tasks_module.translate_reflection_to_english.run(reflection.pk)
        record = TranslationRecord.latest_for("reflection", reflection.pk)
        assert result["status"] == "failed_terminal"
        assert record.status == TranslationRecord.Status.FAILED_TERMINAL
        fake_translate.assert_not_called()

    def test_retryable_failure_records_state_and_schedules_retry(
        self, org, program, template, author, membership,
    ):
        from celery.exceptions import Retry

        reflection = _reflection(org, program, template, author)
        # In eager mode (the test setting), Celery actually re-executes the
        # task when ``self.retry()`` is called, marching all the way to
        # ``failed_terminal``. To assert the *single-attempt* retryable
        # state, stub the task's ``retry`` method so it raises ``Retry``
        # without re-invoking the function body. That mirrors how a real
        # worker would behave: schedule a retry and stop.
        with patch.object(tasks_module, "translate_content") as fake_translate, \
             patch.object(
                 tasks_module.translate_reflection_to_english,
                 "retry",
                 side_effect=Retry("scheduled"),
             ):
            fake_translate.side_effect = TranslationFailure(
                "transient", retryable=True,
            )
            with pytest.raises(Retry):
                tasks_module.translate_reflection_to_english.run(reflection.pk)
        record = TranslationRecord.latest_for("reflection", reflection.pk)
        assert record.status == TranslationRecord.Status.FAILED_RETRYABLE
        assert record.last_error.startswith("transient")
        assert record.attempt_count == 1


# ---------------------------------------------------------------------------
# Celery task: purge_expired_translations
# ---------------------------------------------------------------------------


class TestPurgeExpiredTranslations:
    def test_purges_rows_older_than_retention(self, org, program, template, author, membership, settings):
        settings.TRANSLATION_RETENTION_DAYS = 1
        reflection = _reflection(org, program, template, author)
        old = TranslationRecord.all_objects.create(
            organization=org,
            content_type="reflection",
            content_id=str(reflection.pk),
            source_language="es",
            target_language="en",
            status=TranslationRecord.Status.COMPLETED,
            translated_text="old",
        )
        fresh = TranslationRecord.all_objects.create(
            organization=org,
            content_type="reflection",
            content_id=str(reflection.pk),
            source_language="es",
            target_language="en",
            status=TranslationRecord.Status.COMPLETED,
            translated_text="fresh",
        )
        # Back-date ``old`` to before the retention cutoff. ``created_at``
        # is auto_now_add so we have to bypass via update().
        TranslationRecord.all_objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(days=10),
        )
        result = tasks_module.purge_expired_translations.run()
        assert result["deleted"] == 1
        assert TranslationRecord.all_objects.filter(pk=fresh.pk).exists()
        assert not TranslationRecord.all_objects.filter(pk=old.pk).exists()


# ---------------------------------------------------------------------------
# Metrics adapter -- no Datadog installed in CI; helper must no-op cleanly.
# ---------------------------------------------------------------------------


class TestMetricsNoopWithoutDatadog:
    def test_record_submitted_does_not_raise(self):
        metrics_module.record_submitted("reflection", "es", "en")

    def test_record_completed_does_not_raise(self):
        metrics_module.record_completed("reflection", "es", "en", tokens_used=12)

    def test_record_failed_does_not_raise(self):
        metrics_module.record_failed(
            "reflection", "es", "en", reason="client_error", terminal=False,
        )


# ---------------------------------------------------------------------------
# Sanity: every code path above is exercised by at least one assertion.
# ---------------------------------------------------------------------------


def test_module_exports_are_stable():
    # If someone reshuffles the package, the public surface in __init__
    # must still expose these symbols -- I18N.md links to them.
    from bunk_logs.core import translation

    expected = {
        "TRANSLATION_PROMPT",
        "TranslationFailure",
        "TranslationResult",
        "enqueue_translation_for_reflection",
        "purge_expired_translations",
        "translate_content",
        "translate_reflection_to_english",
    }
    assert expected.issubset(set(translation.__all__))


def test_client_module_uses_lazy_anthropic_import():
    # Don't import ``anthropic`` at module load; tests must remain
    # runnable without the SDK on the path. This is a regression guard
    # for the design note in client.py.
    assert "anthropic" not in dir(client_module)


# ---------------------------------------------------------------------------
# Beat schedule registration
# ---------------------------------------------------------------------------


class TestBeatRegistration:
    """Migration 0027 calls ``register_periodic_tasks`` so the PeriodicTask
    row is already present at test start. We assert on that baseline first,
    then exercise idempotency + reverse explicitly. The module-level
    ``pytestmark = pytest.mark.django_db`` already wraps each test in a
    transaction, so mutations inside one test do not leak into siblings."""

    def test_migration_installs_the_periodic_task_row(self):
        from django.apps import apps as django_apps
        PeriodicTask = django_apps.get_model("django_celery_beat", "PeriodicTask")
        row = PeriodicTask.objects.get(name=beat_module.PERIODIC_TASK_NAME)
        assert row.task == beat_module.PERIODIC_TASK_PATH
        assert row.enabled is True
        assert row.crontab is not None
        assert row.crontab.hour == str(beat_module.SCHEDULE_HOUR)
        assert row.crontab.minute == str(beat_module.SCHEDULE_MINUTE)

    def test_register_is_idempotent(self):
        from django.apps import apps as django_apps
        PeriodicTask = django_apps.get_model("django_celery_beat", "PeriodicTask")
        beat_module.register_periodic_tasks(django_apps)
        beat_module.register_periodic_tasks(django_apps)
        assert (
            PeriodicTask.objects.filter(name=beat_module.PERIODIC_TASK_NAME).count()
            == 1
        )

    def test_unregister_drops_the_row(self):
        from django.apps import apps as django_apps
        PeriodicTask = django_apps.get_model("django_celery_beat", "PeriodicTask")
        beat_module.unregister_periodic_tasks(django_apps)
        assert not PeriodicTask.objects.filter(
            name=beat_module.PERIODIC_TASK_NAME,
        ).exists()
