"""Datadog metric emission for the translation pipeline (Step 7_5).

Wrapped behind helpers so call sites stay terse and so swapping the metric
sink (Datadog -> StatsD -> Prometheus) is a single-file change. All metric
names live here as constants -- ``I18N.md`` references them.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

logger = logging.getLogger(__name__)

METRIC_SUBMITTED = "bunklogs.translation.submitted"
METRIC_COMPLETED = "bunklogs.translation.completed"
METRIC_FAILED = "bunklogs.translation.failed"
METRIC_TOKENS_USED = "bunklogs.translation.tokens_used"


def _emit_counter(name: str, value: int = 1, tags: Iterable[str] | None = None) -> None:
    """Increment a Datadog counter, swallowing import errors gracefully.

    The Celery worker may run without ``datadog`` configured (tests, local
    dev); in that case we log at DEBUG instead of raising so translation
    keeps working.
    """
    try:
        from datadog import statsd  # type: ignore[import-not-found]
    except ImportError:
        logger.debug("datadog not available; skipping metric %s", name)
        return
    try:
        statsd.increment(name, value=value, tags=list(tags) if tags else None)
    except Exception:
        logger.exception("datadog statsd.increment failed for %s", name)


def _emit_distribution(
    name: str, value: float, tags: Iterable[str] | None = None,
) -> None:
    try:
        from datadog import statsd  # type: ignore[import-not-found]
    except ImportError:
        logger.debug("datadog not available; skipping metric %s", name)
        return
    try:
        statsd.distribution(name, value=value, tags=list(tags) if tags else None)
    except Exception:
        logger.exception("datadog statsd.distribution failed for %s", name)


def _content_tags(content_type: str, source_language: str, target_language: str) -> list[str]:
    return [
        f"content_type:{content_type}",
        f"source_language:{source_language}",
        f"target_language:{target_language}",
    ]


def record_submitted(content_type: str, source_language: str, target_language: str) -> None:
    _emit_counter(
        METRIC_SUBMITTED,
        tags=_content_tags(content_type, source_language, target_language),
    )


def record_completed(
    content_type: str, source_language: str, target_language: str, *, tokens_used: int,
) -> None:
    tags = _content_tags(content_type, source_language, target_language)
    _emit_counter(METRIC_COMPLETED, tags=tags)
    if tokens_used:
        _emit_distribution(METRIC_TOKENS_USED, tokens_used, tags=tags)


def record_failed(
    content_type: str,
    source_language: str,
    target_language: str,
    *,
    reason: str,
    terminal: bool,
) -> None:
    tags = _content_tags(content_type, source_language, target_language) + [
        f"reason:{reason}",
        f"terminal:{'true' if terminal else 'false'}",
    ]
    _emit_counter(METRIC_FAILED, tags=tags)
