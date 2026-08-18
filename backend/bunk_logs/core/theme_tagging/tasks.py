"""Celery tasks for the reflection theme-tagging pipeline.

* :func:`tag_reflection_themes` -- per-reflection task. Loads the reflection,
  extracts its taggable free-text fields, calls the synchronous helper, and
  replaces the :class:`ReflectionThemeTag` rows for the current taxonomy
  version. Retries with the same 1/5/30-minute backoff as auto-translation;
  jumps straight to ``failed_terminal`` for non-retryable errors.
* :func:`enqueue_theme_tagging_for_reflection` -- application-side helper
  that revokes any pending task and enqueues a fresh one (re-tagging on
  edit), gated on the template allowlist so tagging cost stays bounded.
"""

from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionThemeTag
from bunk_logs.core.models import ReflectionThemeTagging
from bunk_logs.core.theme_tagging.client import ThemeTaggingFailureError
from bunk_logs.core.theme_tagging.client import tag_reflection_text
from bunk_logs.core.theme_tagging.metrics import record_completed
from bunk_logs.core.theme_tagging.metrics import record_failed
from bunk_logs.core.theme_tagging.metrics import record_submitted
from bunk_logs.core.theme_tagging.taxonomy import TAXONOMY_VERSION
from bunk_logs.core.theme_tagging.taxonomy import taggable_fields

logger = logging.getLogger(__name__)

# Backoff matches auto-translation: 1 min, 5 min, 30 min.
RETRY_BACKOFF_SECONDS: tuple[int, ...] = (60, 300, 1800)

DEFAULT_TEMPLATE_SLUGS: tuple[str, ...] = ("tbe-madrich-3-2-1-weekly",)


def _soft_time_limit() -> int:
    return int(getattr(settings, "THEME_TAGGING_TASK_SOFT_TIME_LIMIT_SECONDS", 30))


def _max_retries() -> int:
    return int(getattr(settings, "THEME_TAGGING_TASK_MAX_RETRIES", 3))


def _allowed_template_slugs() -> tuple[str, ...]:
    configured = getattr(settings, "THEME_TAGGING_TEMPLATE_SLUGS", None)
    if not configured:
        return DEFAULT_TEMPLATE_SLUGS
    return tuple(str(slug).strip() for slug in configured if str(slug).strip())


def is_taggable_reflection(reflection: Reflection) -> bool:
    """True when ``reflection`` belongs to an allowlisted template with text fields.

    The allowlist is the cost gate: only templates we actually build a growth
    dashboard for are worth spending LLM calls on.
    """
    template = getattr(reflection, "template", None)
    if template is None:
        return False
    if template.slug not in _allowed_template_slugs():
        return False
    return bool(taggable_fields(template.schema))


def extract_taggable_items(reflection: Reflection) -> list[tuple[str, str]]:
    """Flatten a reflection's taggable answers into ``(field_key, text)`` pairs.

    ``text_list`` answers are joined into one entry per field, because tags
    are recorded per field rather than per list item.
    """
    answers = reflection.answers or {}
    if not isinstance(answers, dict):
        return []
    items: list[tuple[str, str]] = []
    for field in taggable_fields(reflection.template.schema):
        value = answers.get(field["key"])
        if isinstance(value, str):
            text = value.strip()
        elif isinstance(value, list):
            text = "; ".join(
                part.strip() for part in value if isinstance(part, str) and part.strip()
            )
        else:
            continue
        if text:
            items.append((field["key"], text))
    return items


def resolve_grade_level(reflection: Reflection) -> int | None:
    """Grade level of the reflection's author within its program, or None.

    Resolved once at tag time and denormalized onto the tag rows -- see the
    :class:`ReflectionThemeTag` docstring for why point-in-time capture is
    the correct semantics here.
    """
    if not reflection.author_id or not reflection.program_id:
        return None
    return (
        Membership.all_objects.filter(
            program_id=reflection.program_id,
            person_id=reflection.author_id,
            grade_level__isnull=False,
        )
        .order_by("-is_active", "-created_at")
        .values_list("grade_level", flat=True)
        .first()
    )


def _dashboard_roles(reflection: Reflection) -> dict[str, str]:
    return {
        field["key"]: field["dashboard_role"]
        for field in taggable_fields(reflection.template.schema)
    }


@shared_task(
    bind=True,
    name="bunk_logs.core.theme_tagging.tag_reflection_themes",
    soft_time_limit=30,  # overridden at runtime via apply_async
)
def tag_reflection_themes(self, reflection_id: int) -> dict:
    """Tag a single Reflection's free-text answers against the theme taxonomy.

    Idempotent on the (reflection, taxonomy_version) tagging row: tags are
    deleted and rewritten inside one transaction, so a double-execution
    converges rather than duplicating.
    """
    try:
        reflection = Reflection.all_objects.select_related(
            "organization", "template", "program",
        ).get(pk=reflection_id)
    except Reflection.DoesNotExist:
        logger.warning(
            "tag_reflection_themes: reflection %s not found (deleted?)",
            reflection_id,
        )
        return {"status": "skipped", "reason": "reflection_missing"}

    if not is_taggable_reflection(reflection):
        logger.debug(
            "tag_reflection_themes: reflection %s template not tagged; skipping",
            reflection_id,
        )
        return {"status": "skipped", "reason": "template_not_tagged"}

    record_submitted(TAXONOMY_VERSION)

    record = ReflectionThemeTagging.latest_for(reflection_id, TAXONOMY_VERSION)
    if record is None:
        record = ReflectionThemeTagging.all_objects.create(
            organization=reflection.organization,
            reflection=reflection,
            taxonomy_version=TAXONOMY_VERSION,
            status=ReflectionThemeTagging.Status.PENDING,
            celery_task_id=self.request.id or "",
        )
    else:
        ReflectionThemeTagging.all_objects.filter(pk=record.pk).update(
            status=ReflectionThemeTagging.Status.PENDING,
            celery_task_id=self.request.id or "",
            updated_at=timezone.now(),
        )
        record.refresh_from_db()

    items = extract_taggable_items(reflection)
    if not items:
        # Nothing to tag -- mark terminal so coverage reporting shows the
        # right state instead of counting this reflection as pending forever.
        _fail(record, "Reflection has no taggable free-text answers.", terminal=True)
        record_failed(TAXONOMY_VERSION, reason="empty_source", terminal=True)
        return {
            "status": "failed_terminal",
            "record_id": str(record.id),
            "reason": "empty_source",
        }

    try:
        result = tag_reflection_text(items)
    except ThemeTaggingFailureError as exc:
        record.attempt_count = (record.attempt_count or 0) + 1
        attempts = record.attempt_count
        if not exc.retryable or attempts >= _max_retries():
            _fail(record, str(exc), terminal=True, bump_attempt=False)
            record_failed(TAXONOMY_VERSION, reason="client_error", terminal=True)
            return {
                "status": "failed_terminal",
                "record_id": str(record.id),
                "reason": str(exc)[:200],
            }
        _fail(record, str(exc), terminal=False, bump_attempt=False)
        record_failed(TAXONOMY_VERSION, reason="client_error", terminal=False)
        # ``attempts`` is 1-indexed because we incremented above; pick the
        # matching countdown.
        countdown = RETRY_BACKOFF_SECONDS[
            min(attempts - 1, len(RETRY_BACKOFF_SECONDS) - 1)
        ]
        raise self.retry(
            exc=exc, countdown=countdown, max_retries=_max_retries() - 1,
        )

    tag_count = _persist_tags(record, reflection, result)

    record.status = ReflectionThemeTagging.Status.COMPLETED
    record.model_id = result.model_id
    record.tokens_used = result.tokens_used
    record.attempt_count = (record.attempt_count or 0) + 1
    record.last_error = ""
    record.save(
        update_fields=[
            "status",
            "model_id",
            "tokens_used",
            "attempt_count",
            "last_error",
            "updated_at",
        ],
    )
    record_completed(
        TAXONOMY_VERSION, tokens_used=result.tokens_used, tag_count=tag_count,
    )
    return {
        "status": "completed",
        "record_id": str(record.id),
        "tags": tag_count,
        "tokens_used": result.tokens_used,
    }


def _persist_tags(record, reflection: Reflection, result) -> int:
    """Replace the tag rows for ``record`` with the tagger's output.

    Delete-then-insert keeps re-tagging simple and makes the task
    idempotent: whatever the model returned this run is the whole truth for
    this (reflection, taxonomy_version).
    """
    roles = _dashboard_roles(reflection)
    grade_level = resolve_grade_level(reflection)
    rows = [
        ReflectionThemeTag(
            tagging=record,
            organization=reflection.organization,
            reflection=reflection,
            program=reflection.program,
            field_key=field_key,
            dashboard_role=roles.get(field_key, ""),
            theme_key=theme_key,
            grade_level=grade_level,
            period_start=reflection.period_start,
        )
        for field_key, theme_keys in result.themes_by_field.items()
        for theme_key in theme_keys
        if field_key in roles
    ]
    with transaction.atomic():
        ReflectionThemeTag.all_objects.filter(tagging=record).delete()
        if rows:
            ReflectionThemeTag.all_objects.bulk_create(rows)
    return len(rows)


def _fail(record, message: str, *, terminal: bool, bump_attempt: bool = True) -> None:
    record.status = (
        ReflectionThemeTagging.Status.FAILED_TERMINAL
        if terminal
        else ReflectionThemeTagging.Status.FAILED_RETRYABLE
    )
    record.last_error = message[:2000]
    if bump_attempt:
        record.attempt_count = (record.attempt_count or 0) + 1
    record.save(
        update_fields=["status", "last_error", "attempt_count", "updated_at"],
    )


def enqueue_theme_tagging_for_reflection(reflection: Reflection) -> str | None:
    """Cancel any pending tagging for ``reflection`` and enqueue a fresh task.

    Returns the new Celery task id, or ``None`` when the reflection's
    template is not on the tagging allowlist. Safe to call from inside a
    transaction -- the enqueue happens via :func:`transaction.on_commit` so
    the task only runs once the DB row is visible to other workers.
    """
    if not is_taggable_reflection(reflection):
        return None

    pending = ReflectionThemeTagging.latest_for(reflection.pk, TAXONOMY_VERSION)
    if (
        pending
        and pending.status == ReflectionThemeTagging.Status.PENDING
        and pending.celery_task_id
    ):
        _revoke_task(pending.celery_task_id)

    soft_time_limit = _soft_time_limit()

    async_result_holder: dict[str, str] = {}

    def _do_enqueue() -> None:
        async_result = tag_reflection_themes.apply_async(
            args=[reflection.pk],
            soft_time_limit=soft_time_limit,
            time_limit=soft_time_limit + 30,
        )
        async_result_holder["id"] = async_result.id

    transaction.on_commit(_do_enqueue)
    return async_result_holder.get("id")


def _revoke_task(task_id: str) -> None:
    """Best-effort task revocation -- swallow broker errors.

    The worker may pick up the task before the revoke lands; the task is
    idempotent (delete-then-insert tags) so a double-execution is harmless,
    just wasteful.
    """
    try:
        from celery.result import AsyncResult

        AsyncResult(task_id).revoke()
    except Exception:
        logger.exception("Failed to revoke theme tagging task %s", task_id)
