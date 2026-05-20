"""Celery tasks for the auto-translation pipeline (Step 7_5).

* :func:`translate_reflection_to_english` -- per-reflection task. Loads the
  reflection, builds the source text, calls the synchronous helper, and
  persists / updates the :class:`TranslationRecord`. Retries with Celery's
  exponential backoff on transient failures; jumps straight to
  ``failed_terminal`` for non-retryable errors (auth, empty input).
* :func:`enqueue_translation_for_reflection` -- application-side helper that
  revokes any pending task and enqueues a fresh one (re-translation on
  edit, per spec).
* :func:`purge_expired_translations` -- nightly GC task wired through
  Celery Beat (see :mod:`bunk_logs.core.translation.beat`).
"""

from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from bunk_logs.core.models import Reflection
from bunk_logs.core.models import TranslationRecord
from bunk_logs.core.translation.client import TranslationFailure
from bunk_logs.core.translation.client import translate_content
from bunk_logs.core.translation.metrics import record_completed
from bunk_logs.core.translation.metrics import record_failed
from bunk_logs.core.translation.metrics import record_submitted

logger = logging.getLogger(__name__)

# Backoff matches the spec exactly: 1 min, 5 min, 30 min. Celery's
# ``Task.retry(countdown=...)`` honours these.
RETRY_BACKOFF_SECONDS: tuple[int, ...] = (60, 300, 1800)

REFLECTION_CONTENT_TYPE = "reflection"


def _soft_time_limit() -> int:
    return int(getattr(settings, "TRANSLATION_TASK_SOFT_TIME_LIMIT_SECONDS", 30))


def _max_retries() -> int:
    return int(getattr(settings, "TRANSLATION_TASK_MAX_RETRIES", 3))


def _retention_days() -> int:
    return int(getattr(settings, "TRANSLATION_RETENTION_DAYS", 90))


def _reflection_source_text(reflection: Reflection) -> str:
    """Flatten a reflection's answers JSON into a single translatable string.

    The translation prompt expects a paragraph-shaped blob. We join the
    template fields with the field key as a heading so reviewers can match
    translated paragraphs back to their original form questions without
    needing the template open.
    """
    answers = reflection.answers or {}
    if not isinstance(answers, dict):
        return str(answers)
    parts: list[str] = []
    for key, value in answers.items():
        if value in (None, ""):
            continue
        if isinstance(value, str) and not value.strip():
            # Whitespace-only answers carry no translatable content.
            # Treat as empty so the task can short-circuit to terminal
            # rather than spending a translation request on padding.
            continue
        if isinstance(value, (dict, list)):
            # Skip non-text answers (rating groups, etc.). Translation only
            # makes sense for free-text fields; readers see numeric fields
            # in their original form regardless.
            continue
        parts.append(f"## {key}\n{value!s}")
    return "\n\n".join(parts).strip()


@shared_task(
    bind=True,
    name="bunk_logs.core.translation.translate_reflection_to_english",
    soft_time_limit=30,  # overridden at runtime via apply_async
)
def translate_reflection_to_english(self, reflection_id: int) -> dict:
    """Translate a single Reflection's free-text answers to English.

    Idempotent on the latest TranslationRecord for the reflection: if a
    completed translation already exists for the current content, the
    task no-ops and returns its id. Otherwise it (re)uses the latest
    pending row or creates a new one.
    """
    try:
        reflection = Reflection.all_objects.select_related("organization").get(
            pk=reflection_id,
        )
    except Reflection.DoesNotExist:
        logger.warning(
            "translate_reflection_to_english: reflection %s not found (deleted?)",
            reflection_id,
        )
        return {"status": "skipped", "reason": "reflection_missing"}

    source_language = reflection.language or "en"
    if source_language == "en":
        logger.debug(
            "translate_reflection_to_english: reflection %s is English; skipping",
            reflection_id,
        )
        return {"status": "skipped", "reason": "already_english"}

    record_submitted(REFLECTION_CONTENT_TYPE, source_language, "en")

    record = TranslationRecord.latest_for(
        REFLECTION_CONTENT_TYPE, reflection_id,
    )
    if record is None or record.status == TranslationRecord.Status.COMPLETED:
        record = TranslationRecord.all_objects.create(
            organization=reflection.organization,
            content_type=REFLECTION_CONTENT_TYPE,
            content_id=str(reflection_id),
            source_language=source_language,
            target_language="en",
            status=TranslationRecord.Status.PENDING,
            celery_task_id=self.request.id or "",
        )
    else:
        TranslationRecord.all_objects.filter(pk=record.pk).update(
            status=TranslationRecord.Status.PENDING,
            celery_task_id=self.request.id or "",
            updated_at=timezone.now(),
        )
        record.refresh_from_db()

    source_text = _reflection_source_text(reflection)
    if not source_text:
        # Nothing translatable -- mark terminal so the UI shows the right
        # state instead of spinning forever.
        record.status = TranslationRecord.Status.FAILED_TERMINAL
        record.last_error = "Reflection has no free-text answers to translate."
        record.attempt_count = (record.attempt_count or 0) + 1
        record.save(
            update_fields=["status", "last_error", "attempt_count", "updated_at"],
        )
        record_failed(
            REFLECTION_CONTENT_TYPE, source_language, "en",
            reason="empty_source", terminal=True,
        )
        return {
            "status": "failed_terminal",
            "record_id": str(record.id),
            "reason": "empty_source",
        }

    try:
        result = translate_content(
            source_text, source_language=source_language, target_language="en",
        )
    except TranslationFailure as exc:
        record.attempt_count = (record.attempt_count or 0) + 1
        record.last_error = str(exc)[:2000]
        attempts = record.attempt_count
        if not exc.retryable or attempts >= _max_retries():
            record.status = TranslationRecord.Status.FAILED_TERMINAL
            record.save(
                update_fields=[
                    "status", "last_error", "attempt_count", "updated_at",
                ],
            )
            record_failed(
                REFLECTION_CONTENT_TYPE, source_language, "en",
                reason="client_error", terminal=True,
            )
            return {
                "status": "failed_terminal",
                "record_id": str(record.id),
                "reason": str(exc)[:200],
            }
        record.status = TranslationRecord.Status.FAILED_RETRYABLE
        record.save(
            update_fields=["status", "last_error", "attempt_count", "updated_at"],
        )
        record_failed(
            REFLECTION_CONTENT_TYPE, source_language, "en",
            reason="client_error", terminal=False,
        )
        # Spec backoff: 60s -> 300s -> 1800s. ``attempts`` is 1-indexed
        # because we incremented above; pick the matching countdown.
        countdown = RETRY_BACKOFF_SECONDS[min(attempts - 1, len(RETRY_BACKOFF_SECONDS) - 1)]
        raise self.retry(
            exc=exc, countdown=countdown, max_retries=_max_retries() - 1,
        )

    record.status = TranslationRecord.Status.COMPLETED
    record.translated_text = result.text
    record.model_id = result.model_id
    record.tokens_used = result.tokens_used
    record.attempt_count = (record.attempt_count or 0) + 1
    record.last_error = ""
    record.save(
        update_fields=[
            "status",
            "translated_text",
            "model_id",
            "tokens_used",
            "attempt_count",
            "last_error",
            "updated_at",
        ],
    )
    record_completed(
        REFLECTION_CONTENT_TYPE, source_language, "en",
        tokens_used=result.tokens_used,
    )
    return {
        "status": "completed",
        "record_id": str(record.id),
        "tokens_used": result.tokens_used,
    }


def enqueue_translation_for_reflection(reflection: Reflection) -> str | None:
    """Cancel any pending translation for ``reflection`` and enqueue a fresh task.

    Returns the new Celery task id (or ``None`` when the reflection is
    English-only and no task is needed). Safe to call from inside a
    transaction -- the actual enqueue happens via
    :func:`transaction.on_commit` so the task only runs once the DB row
    is visible to other workers.
    """
    if (reflection.language or "en") == "en":
        return None

    pending = TranslationRecord.latest_for(
        REFLECTION_CONTENT_TYPE, reflection.pk,
    )
    if pending and pending.status == TranslationRecord.Status.PENDING and pending.celery_task_id:
        _revoke_task(pending.celery_task_id)

    soft_time_limit = _soft_time_limit()

    async_result_holder: dict[str, str] = {}

    def _do_enqueue() -> None:
        async_result = translate_reflection_to_english.apply_async(
            args=[reflection.pk],
            soft_time_limit=soft_time_limit,
            time_limit=soft_time_limit + 30,
        )
        async_result_holder["id"] = async_result.id

    transaction.on_commit(_do_enqueue)
    return async_result_holder.get("id")


def _revoke_task(task_id: str) -> None:
    """Best-effort task revocation -- swallow broker errors.

    The worker may pick up the task before the revoke lands; the task
    itself is idempotent (translate-then-persist) so a double-execution
    is harmless, just wasteful. We still try because the common case
    (large backoff window) wins us a cheap cancellation.
    """
    try:
        from bunk_logs.core.translation.client import logger as _ignored  # noqa: F401
        from celery.result import AsyncResult

        AsyncResult(task_id).revoke()
    except Exception:
        logger.exception("Failed to revoke translation task %s", task_id)


@shared_task(
    name="bunk_logs.core.translation.purge_expired_translations",
)
def purge_expired_translations() -> dict:
    """Drop TranslationRecord rows older than ``TRANSLATION_RETENTION_DAYS``.

    Wired into Celery Beat by ``bunk_logs.core.translation.beat`` (loaded
    from ``django_celery_beat`` Schedules, not in-process Beat). The task
    is idempotent: it returns the number of rows deleted so monitoring
    can alarm if storage grows unexpectedly.
    """
    cutoff = timezone.now() - timedelta(days=_retention_days())
    deleted, _ = TranslationRecord.all_objects.filter(created_at__lt=cutoff).delete()
    logger.info(
        "purge_expired_translations: deleted %s rows older than %s",
        deleted, cutoff.isoformat(),
    )
    return {"deleted": deleted, "cutoff": cutoff.isoformat()}
