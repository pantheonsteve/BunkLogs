"""Datadog metric emission for the theme-tagging pipeline.

Wrapped behind helpers so call sites stay terse and so swapping the metric
sink is a single-file change, matching
:mod:`bunk_logs.core.translation.metrics`.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

logger = logging.getLogger(__name__)

METRIC_SUBMITTED = "bunklogs.theme_tagging.submitted"
METRIC_COMPLETED = "bunklogs.theme_tagging.completed"
METRIC_FAILED = "bunklogs.theme_tagging.failed"
METRIC_TOKENS_USED = "bunklogs.theme_tagging.tokens_used"


def _emit_counter(name: str, value: int = 1, tags: Iterable[str] | None = None) -> None:
    """Increment a Datadog counter, swallowing import errors gracefully.

    The Celery worker may run without ``datadog`` configured (tests, local
    dev); in that case we log at DEBUG instead of raising so tagging keeps
    working.
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


def _base_tags(taxonomy_version: str) -> list[str]:
    return [f"taxonomy_version:{taxonomy_version}"]


def record_submitted(taxonomy_version: str) -> None:
    _emit_counter(METRIC_SUBMITTED, tags=_base_tags(taxonomy_version))


def record_completed(
    taxonomy_version: str, *, tokens_used: int, tag_count: int,
) -> None:
    tags = _base_tags(taxonomy_version) + [f"tag_count:{tag_count}"]
    _emit_counter(METRIC_COMPLETED, tags=tags)
    if tokens_used:
        _emit_distribution(
            METRIC_TOKENS_USED, tokens_used, tags=_base_tags(taxonomy_version),
        )


def record_failed(taxonomy_version: str, *, reason: str, terminal: bool) -> None:
    tags = _base_tags(taxonomy_version) + [
        f"reason:{reason}",
        f"terminal:{'true' if terminal else 'false'}",
    ]
    _emit_counter(METRIC_FAILED, tags=tags)
