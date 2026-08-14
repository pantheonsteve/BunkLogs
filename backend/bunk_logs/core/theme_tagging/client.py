"""Synchronous Anthropic theme-tagging helper.

Isolated from Django models / Celery so it stays unit-testable with a small
mock surface (one ``messages.create`` call), matching the auto-translation
boundary in :mod:`bunk_logs.core.translation.client`.

Key design choices:

* One request per reflection covering every taggable field at once. Tagging
  fields separately would triple the call count for no accuracy gain.
* The model is asked for strict JSON and its output is validated against the
  taxonomy: unknown keys are dropped rather than trusted, so a model that
  invents a category can never widen the taxonomy behind our back.
* Failures bubble as :class:`ThemeTaggingFailureError` with a ``retryable``
  flag so the Celery wrapper can pick between backoff and terminal failure.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from django.conf import settings

from bunk_logs.core.theme_tagging.taxonomy import MAX_THEMES_PER_FIELD
from bunk_logs.core.theme_tagging.taxonomy import THEME_TAXONOMY_V1
from bunk_logs.core.theme_tagging.taxonomy import is_valid_theme
from bunk_logs.core.theme_tagging.taxonomy import theme_label

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-sonnet-4-5"

MAX_TOKENS = 1024

# Rough characters-per-token ratio, used only by the backfill command's
# pre-flight cost estimate. Not load-bearing for correctness.
CHARS_PER_TOKEN = 4

TAGGING_PROMPT = (
    "You are categorising weekly self-reflections written by Jewish "
    "religious-school teen assistants (Madrichim, grades 8-12) so their "
    "Director can see how concerns differ by grade.\n\n"
    "Assign each numbered entry below one or more themes from this fixed "
    "list. Use only these theme keys:\n\n"
    "{taxonomy}\n\n"
    "Rules:\n"
    "- Choose at most {max_themes} themes per entry, most relevant first.\n"
    "- Use 'other' only when no other theme genuinely applies.\n"
    "- Judge what the entry is ABOUT, not whether it is positive or negative.\n"
    "- Do not invent theme keys. Do not explain your reasoning.\n\n"
    "Return only a JSON object mapping each entry number (as a string) to an "
    'array of theme keys, e.g. {{"1": ["classroom_management"], '
    '"2": ["lesson_content", "own_confidence"]}}.\n\n'
    "Entries:\n{entries}"
)


@dataclass(frozen=True)
class ThemeTaggingResult:
    """Successful response from :func:`tag_reflection_text`.

    ``themes_by_field`` maps a template field key to its validated theme
    keys. Fields the model omitted are absent rather than empty.
    """

    themes_by_field: dict[str, list[str]]
    model_id: str
    tokens_used: int


class ThemeTaggingFailureError(Exception):
    """Raised when the tagging call fails for any reason.

    ``retryable`` lets the Celery task decide between exponential backoff
    and an immediate terminal failure (e.g. missing credentials, empty
    input, or a response we could not parse).
    """

    def __init__(self, message: str, *, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable


def _taxonomy_block() -> str:
    return "\n".join(
        f"- {theme['key']}: {theme_label(theme['key'])}"
        for theme in THEME_TAXONOMY_V1
    )


def _build_prompt(items: list[tuple[str, str]]) -> str:
    entries = "\n".join(
        f"{index}. {text}" for index, (_field_key, text) in enumerate(items, start=1)
    )
    return TAGGING_PROMPT.format(
        taxonomy=_taxonomy_block(),
        max_themes=MAX_THEMES_PER_FIELD,
        entries=entries,
    )


def estimate_tokens(items: list[tuple[str, str]]) -> int:
    """Rough input-token estimate for a single tagging call.

    Used by ``backfill_reflection_themes`` to print a pre-flight cost
    figure. Deliberately crude -- it exists so an operator does not fire a
    few thousand LLM calls blind.
    """
    if not items:
        return 0
    prompt = _build_prompt(items)
    return max(1, len(prompt) // CHARS_PER_TOKEN) + MAX_TOKENS


def tag_reflection_text(
    items: list[tuple[str, str]],
    *,
    model_id: str | None = None,
    client=None,
) -> ThemeTaggingResult:
    """Tag ``items`` -- a list of ``(field_key, text)`` pairs -- with themes.

    Returns a :class:`ThemeTaggingResult` whose ``themes_by_field`` only ever
    contains keys from the current taxonomy. Raises
    :class:`ThemeTaggingFailureError` on any error; the ``retryable`` flag
    tells the Celery wrapper which retry path to take.

    ``client`` is an optional pre-built Anthropic client (used by tests to
    inject a stub without monkey-patching the SDK). ``model_id`` overrides
    the configured ``ANTHROPIC_THEME_TAGGING_MODEL`` when provided.
    """
    cleaned = [
        (field_key, text.strip())
        for field_key, text in items
        if isinstance(text, str) and text.strip()
    ]
    if not cleaned:
        msg = "tag_reflection_text: no non-empty text to tag"
        raise ThemeTaggingFailureError(msg, retryable=False)

    model = model_id or getattr(
        settings, "ANTHROPIC_THEME_TAGGING_MODEL", DEFAULT_MODEL,
    )

    if client is None:
        client = _build_client()

    prompt = _build_prompt(cleaned)
    try:
        response = client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:
        # network / status / decoding errors all surface here. Treat as
        # retryable so the Celery backoff schedule absorbs transient flakes.
        retryable = not _looks_like_auth_error(exc)
        msg = f"Anthropic theme-tagging request failed: {exc}"
        raise ThemeTaggingFailureError(msg, retryable=retryable) from exc

    raw = _extract_text(response)
    if not raw:
        msg = "Anthropic returned an empty theme-tagging response."
        raise ThemeTaggingFailureError(msg, retryable=True)

    parsed = _parse_response(raw)
    themes_by_field = _validate_themes(parsed, cleaned)
    return ThemeTaggingResult(
        themes_by_field=themes_by_field,
        model_id=model,
        tokens_used=_extract_tokens(response),
    )


def _parse_response(raw: str) -> dict:
    """Parse the model's JSON, tolerating a markdown code fence around it."""
    candidate = raw.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", candidate, re.DOTALL)
    if fence:
        candidate = fence.group(1).strip()
    try:
        parsed = json.loads(candidate)
    except (TypeError, ValueError) as exc:
        # Non-JSON output is a prompt/model problem, not a transient one --
        # retrying the identical prompt will very likely fail the same way.
        msg = f"Could not parse theme-tagging response as JSON: {exc}"
        raise ThemeTaggingFailureError(msg, retryable=False) from exc
    if not isinstance(parsed, dict):
        msg = f"Theme-tagging response was {type(parsed).__name__}, expected object."
        raise ThemeTaggingFailureError(msg, retryable=False)
    return parsed


def _validate_themes(
    parsed: dict, items: list[tuple[str, str]],
) -> dict[str, list[str]]:
    """Map the model's 1-indexed entry numbers back to field keys.

    Unknown theme keys and out-of-range entry numbers are dropped with a
    warning rather than raising: a partially-usable tagging beats discarding
    the whole reflection because the model hallucinated one category.
    """
    out: dict[str, list[str]] = {}
    for raw_index, raw_themes in parsed.items():
        try:
            position = int(str(raw_index).strip())
        except (TypeError, ValueError):
            logger.warning("theme tagging: non-numeric entry key %r", raw_index)
            continue
        if not 1 <= position <= len(items):
            logger.warning("theme tagging: entry %s out of range", position)
            continue
        field_key = items[position - 1][0]

        if isinstance(raw_themes, str):
            raw_themes = [raw_themes]
        if not isinstance(raw_themes, list):
            logger.warning("theme tagging: entry %s themes not a list", position)
            continue

        seen: list[str] = []
        for theme in raw_themes:
            if not isinstance(theme, str):
                continue
            key = theme.strip()
            if not is_valid_theme(key):
                logger.warning("theme tagging: dropping unknown theme %r", key)
                continue
            if key not in seen:
                seen.append(key)
        if seen:
            out[field_key] = seen[:MAX_THEMES_PER_FIELD]
    return out


def _build_client():
    """Lazily import + construct the Anthropic SDK client.

    Raises :class:`ThemeTaggingFailureError` with ``retryable=False`` if the
    SDK isn't installed or the API key is unset. Keeping the import inside
    the function means unit tests can run without ``anthropic`` on the path
    as long as they inject ``client=...``.
    """
    api_key = getattr(settings, "ANTHROPIC_API_KEY", "")
    if not api_key:
        msg = (
            "ANTHROPIC_API_KEY is not configured; theme tagging cannot run. "
            "Set it in the Django environment or pass an explicit client= "
            "argument."
        )
        raise ThemeTaggingFailureError(msg, retryable=False)
    try:
        from anthropic import Anthropic  # type: ignore[import-not-found]
    except ImportError as exc:
        msg = (
            "anthropic SDK is not installed; pip install anthropic or pass "
            "client= to tag_reflection_text for tests."
        )
        raise ThemeTaggingFailureError(msg, retryable=False) from exc
    return Anthropic(api_key=api_key)


def _extract_text(response) -> str:
    """Pull the assistant text out of an Anthropic Messages response."""
    content = getattr(response, "content", None)
    if isinstance(content, str):
        return content.strip()
    if not content:
        return ""
    parts: list[str] = []
    for block in content:
        block_type = getattr(block, "type", None) or (
            block.get("type") if isinstance(block, dict) else None
        )
        if block_type != "text":
            continue
        text = getattr(block, "text", None)
        if text is None and isinstance(block, dict):
            text = block.get("text")
        if text:
            parts.append(str(text))
    return "\n".join(parts).strip()


def _extract_tokens(response) -> int:
    usage = getattr(response, "usage", None)
    if usage is None:
        return 0
    in_tokens = getattr(usage, "input_tokens", 0) or 0
    out_tokens = getattr(usage, "output_tokens", 0) or 0
    return int(in_tokens) + int(out_tokens)


def _looks_like_auth_error(exc: Exception) -> bool:
    """Heuristic: 401 / 403 / "authentication" failures are non-retryable."""
    name = type(exc).__name__.lower()
    return any(
        key in name for key in ("auth", "permission", "forbidden", "invalidrequest")
    )
