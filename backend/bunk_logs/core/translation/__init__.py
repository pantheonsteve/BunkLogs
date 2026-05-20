"""Auto-translation primitives (Step 7_5).

Public surface:

* :func:`translate_content` -- synchronous helper that talks to the Anthropic
  API and returns ``(translated_text, model_id, tokens_used)``.
* :func:`translate_reflection_to_english` -- Celery task: wraps the helper,
  persists / updates the :class:`TranslationRecord`, emits Datadog metrics,
  retries with exponential backoff, and surfaces terminal failures to the
  reader-side state machine (Story 44).
* :func:`enqueue_translation_for_reflection` -- helper for view code that
  cancels any pending task before enqueueing a fresh one (re-translation on
  edit, per spec).
* :func:`purge_expired_translations` -- nightly Celery Beat task that drops
  TranslationRecord rows older than ``TRANSLATION_RETENTION_DAYS``.

Each module stays focused: ``client`` knows about Anthropic, ``tasks`` knows
about Celery + persistence, ``metrics`` knows about Datadog -- so swapping
any one out (e.g. moving translation to a different LLM, or to a sync HTTP
path) is a single-file change.
"""

from bunk_logs.core.translation.client import TRANSLATION_PROMPT
from bunk_logs.core.translation.client import TranslationFailureError
from bunk_logs.core.translation.client import TranslationResult
from bunk_logs.core.translation.client import translate_content
from bunk_logs.core.translation.tasks import enqueue_translation_for_reflection
from bunk_logs.core.translation.tasks import purge_expired_translations
from bunk_logs.core.translation.tasks import translate_reflection_to_english

__all__ = [
    "TRANSLATION_PROMPT",
    "TranslationFailureError",
    "TranslationResult",
    "enqueue_translation_for_reflection",
    "purge_expired_translations",
    "translate_content",
    "translate_reflection_to_english",
]
