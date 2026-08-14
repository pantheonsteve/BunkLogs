"""LLM theme tagging for reflections (Growth Dashboard by Grade Level).

Free-text reflection answers can't be grouped, so an Anthropic-backed Celery
task tags each one against a fixed taxonomy and the admin growth dashboard
aggregates the resulting :class:`~bunk_logs.core.models.ReflectionThemeTag`
rows by grade level.

Layered so each concern is swappable in one file: :mod:`taxonomy` owns the
categories, :mod:`client` owns the LLM boundary, :mod:`tasks` owns Celery and
persistence, :mod:`metrics` owns the observability sink.
"""

from bunk_logs.core.theme_tagging.client import ThemeTaggingFailureError
from bunk_logs.core.theme_tagging.client import ThemeTaggingResult
from bunk_logs.core.theme_tagging.client import estimate_tokens
from bunk_logs.core.theme_tagging.client import tag_reflection_text
from bunk_logs.core.theme_tagging.tasks import enqueue_theme_tagging_for_reflection
from bunk_logs.core.theme_tagging.tasks import extract_taggable_items
from bunk_logs.core.theme_tagging.tasks import is_taggable_reflection
from bunk_logs.core.theme_tagging.tasks import tag_reflection_themes
from bunk_logs.core.theme_tagging.taxonomy import TAGGED_DASHBOARD_ROLES
from bunk_logs.core.theme_tagging.taxonomy import TAXONOMY_VERSION
from bunk_logs.core.theme_tagging.taxonomy import THEME_TAXONOMY_V1
from bunk_logs.core.theme_tagging.taxonomy import complexity_tier
from bunk_logs.core.theme_tagging.taxonomy import taxonomy_payload
from bunk_logs.core.theme_tagging.taxonomy import theme_label

__all__ = [
    "TAGGED_DASHBOARD_ROLES",
    "TAXONOMY_VERSION",
    "THEME_TAXONOMY_V1",
    "ThemeTaggingFailureError",
    "ThemeTaggingResult",
    "complexity_tier",
    "enqueue_theme_tagging_for_reflection",
    "estimate_tokens",
    "extract_taggable_items",
    "is_taggable_reflection",
    "tag_reflection_text",
    "tag_reflection_themes",
    "taxonomy_payload",
    "theme_label",
]
