"""Synchronous Anthropic translation helper.

Isolated from Django models / Celery so it stays unit-testable with a small
mock surface (one ``messages.create`` call). Callers should prefer the
Celery task wrapper in ``tasks.py`` for any real workflow -- this helper is
the boundary, not the API.

Key design choices:

* The translation prompt lives at module scope (``TRANSLATION_PROMPT``) so
  tests and ``I18N.md`` can quote a single source.
* Failures bubble as :class:`TranslationFailureError` with a ``retryable`` flag
  set by class. Celery's autoretry hooks key off this -- non-retryable
  failures (e.g. missing API key, prompt-too-long) skip the backoff schedule
  and go straight to ``failed_terminal``.
* No global Anthropic client: each call builds a fresh one so test injection
  via ``override_settings`` works and so credentials rotate cleanly without
  Django restarts in long-running workers.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

LANGUAGE_LABELS: dict[str, str] = {
    "en": "English",
    "es": "Spanish",
    "he": "Hebrew",
}

TRANSLATION_PROMPT = (
    "Translate the following text from {source_language} to {target_language}. "
    "Preserve meaning faithfully; do not embellish or summarize. Translate "
    "culturally specific terms with the original in brackets when no clean "
    "English equivalent exists. Preserve the structure of the input "
    "(paragraphs, lists, line breaks). Return only the translation, no "
    "explanatory wrapper.\n\n{content}"
)


@dataclass(frozen=True)
class TranslationResult:
    """Successful response from :func:`translate_content`."""

    text: str
    model_id: str
    tokens_used: int


class TranslationFailureError(Exception):
    """Raised when the translation call fails for any reason.

    ``retryable`` lets the Celery task decide between exponential backoff
    (retryable) and an immediate terminal failure (non-retryable -- e.g.
    missing credentials or invalid input).

    Named with the ``Error`` suffix per ruff N818 / PEP 8 conventions even
    though semantically the failure may be retryable.
    """

    def __init__(self, message: str, *, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable


def _language_label(code: str) -> str:
    return LANGUAGE_LABELS.get(code, code)


def _build_prompt(text: str, source_language: str, target_language: str) -> str:
    return TRANSLATION_PROMPT.format(
        source_language=_language_label(source_language),
        target_language=_language_label(target_language),
        content=text,
    )


def translate_content(
    text: str,
    source_language: str,
    target_language: str = "en",
    *,
    model_id: str | None = None,
    client=None,
) -> TranslationResult:
    """Translate ``text`` from ``source_language`` into ``target_language``.

    Returns a :class:`TranslationResult`. Raises :class:`TranslationFailureError`
    on any error (network, API, parsing); the ``retryable`` flag tells the
    Celery wrapper which retry path to take.

    ``client`` is an optional pre-built Anthropic client (used by tests to
    inject a stub without monkey-patching the SDK). ``model_id`` overrides
    the configured ``ANTHROPIC_TRANSLATION_MODEL`` when provided.
    """
    if not text or not text.strip():
        msg = "translate_content: empty input"
        raise TranslationFailureError(msg, retryable=False)
    if source_language == target_language:
        msg = (
            "translate_content: source and target languages are identical "
            f"({source_language!r}); refusing to translate."
        )
        raise TranslationFailureError(msg, retryable=False)

    model = model_id or getattr(
        settings, "ANTHROPIC_TRANSLATION_MODEL", "claude-sonnet-4-5",
    )

    if client is None:
        client = _build_client()

    prompt = _build_prompt(text, source_language, target_language)
    try:
        response = client.messages.create(
            model=model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:
        # network / status / decoding errors all surface here. Treat as
        # retryable so the Celery backoff schedule absorbs transient flakes.
        retryable = not _looks_like_auth_error(exc)
        msg = f"Anthropic translation request failed: {exc}"
        raise TranslationFailureError(msg, retryable=retryable) from exc

    text_out = _extract_text(response)
    tokens_used = _extract_tokens(response)
    if not text_out:
        msg = "Anthropic returned an empty translation."
        raise TranslationFailureError(msg, retryable=True)

    return TranslationResult(text=text_out, model_id=model, tokens_used=tokens_used)


def _build_client():
    """Lazily import + construct the Anthropic SDK client.

    Raises :class:`TranslationFailureError` with ``retryable=False`` if the SDK
    isn't installed or the API key is unset. Keeping the import inside the
    function means unit tests can run without ``anthropic`` on the path as
    long as they inject ``client=...``.
    """
    api_key = getattr(settings, "ANTHROPIC_API_KEY", "")
    if not api_key:
        msg = (
            "ANTHROPIC_API_KEY is not configured; auto-translation cannot "
            "run. Set it in the Django environment or pass an explicit "
            "client= argument."
        )
        raise TranslationFailureError(msg, retryable=False)
    try:
        from anthropic import Anthropic  # type: ignore[import-not-found]
    except ImportError as exc:
        msg = (
            "anthropic SDK is not installed; pip install anthropic or pass "
            "client= to translate_content for tests."
        )
        raise TranslationFailureError(msg, retryable=False) from exc
    return Anthropic(api_key=api_key)


def _extract_text(response) -> str:
    """Pull the assistant text out of an Anthropic Messages response.

    The SDK returns ``response.content`` as a list of content blocks; we
    concatenate the ``type='text'`` ones (the prompt asks for plain text
    only, but be defensive in case the model emits structured blocks).
    """
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
    """Heuristic: 401 / 403 / "authentication" failures are non-retryable.

    The Anthropic SDK raises typed errors (e.g. ``AuthenticationError``);
    we sniff by class name to avoid a hard import that would couple this
    module to the SDK version, since the helper must remain testable
    without the SDK installed.
    """
    name = type(exc).__name__.lower()
    return any(
        key in name for key in ("auth", "permission", "forbidden", "invalidrequest")
    )
