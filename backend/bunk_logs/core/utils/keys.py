"""Helpers for working with ReflectionTemplate field keys."""
from __future__ import annotations

import re
import unicodedata

_NON_WORD = re.compile(r"[^a-z0-9]+")
_MAX_KEY_LENGTH = 50


def suggest_key_from_prompt(prompt_text: str) -> str:
    """Slugify English prompt text to a snake_case field key.

    Examples:
        "List 3 things you did well" → "list_3_things_you_did_well"
        "What was your biggest highlight?" → "what_was_your_biggest_highlight"

    The result is:
    - Lowercased ASCII (Unicode letters normalized to their ASCII equivalent)
    - Non-alphanumeric runs replaced with underscores
    - Leading/trailing underscores stripped
    - Truncated to 50 characters at a word boundary where possible
    """
    text = unicodedata.normalize("NFKD", prompt_text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = _NON_WORD.sub("_", text)
    text = text.strip("_")

    if len(text) <= _MAX_KEY_LENGTH:
        return text

    truncated = text[:_MAX_KEY_LENGTH]
    last_sep = truncated.rfind("_")
    if last_sep > 0:
        truncated = truncated[:last_sep]
    return truncated.strip("_")
