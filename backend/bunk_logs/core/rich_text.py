"""Helpers for detecting and migrating inline base64 images in rich text.

The Quill editor historically embedded pasted/dropped images as
``<img src="data:image/...;base64,...">`` straight into the HTML that gets
stored in text columns (StaffLog, BunkLog) and reflection ``answers`` JSON.
A single such image can be many megabytes, bloating the DB and breaking
``pg_dump``. New uploads route through S3 instead; these helpers power both the
submission guard (reject new inline base64) and the one-off cleanup command
(extract existing blobs -> S3 -> rewrite ``src`` to the stored URL).
"""

from __future__ import annotations

import base64
import binascii
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

# Matches an <img> ``src`` (single or double quoted) holding a base64 data URI.
# The base64 payload never contains the surrounding quote char, so [^"'] is safe.
_INLINE_IMG_RE = re.compile(
    r"""src\s*=\s*(?P<q>["'])data:image/(?P<mime>[a-zA-Z0-9.+-]+);base64,(?P<data>[^"']+)(?P=q)""",
    re.IGNORECASE,
)

# Cheap membership test for the submission guard (no full match needed).
_DETECT_RE = re.compile(r"data:image/[a-zA-Z0-9.+-]+;base64,", re.IGNORECASE)

_MIME_EXT = {
    "jpeg": ".jpg",
    "jpg": ".jpg",
    "png": ".png",
    "gif": ".gif",
    "webp": ".webp",
    "svg+xml": ".svg",
}


def contains_inline_base64_image(value) -> bool:
    """True if the string contains at least one inline base64 image data URI."""
    return isinstance(value, str) and bool(_DETECT_RE.search(value))


class InlineImage:
    """One matched inline image within a rich-text string."""

    def __init__(self, match: re.Match):
        self._match = match
        self.mime = match.group("mime").lower()
        self._raw_data = match.group("data")

    @property
    def extension(self) -> str:
        return _MIME_EXT.get(self.mime, ".bin")

    def decode(self) -> bytes:
        """Decode the base64 payload to raw bytes (raises on malformed data)."""
        # Strip any stray whitespace some editors insert into the data URI.
        cleaned = re.sub(r"\s+", "", self._raw_data)
        return base64.b64decode(cleaned, validate=True)


def iter_inline_images(html: str) -> Iterator[InlineImage]:
    """Yield each inline base64 image found in ``html`` (in document order)."""
    if not isinstance(html, str):
        return
    for match in _INLINE_IMG_RE.finditer(html):
        yield InlineImage(match)


def replace_inline_images(html: str, upload) -> tuple[str, int]:
    """Rewrite each inline base64 ``<img src>`` in ``html`` to a hosted URL.

    ``upload`` is called as ``upload(image: InlineImage) -> str`` and must return
    the URL to substitute. Returns ``(new_html, num_replaced)``. Malformed data
    URIs are left untouched (and not counted) so a single bad blob can't abort a
    batch. Idempotent: re-running finds no ``data:image`` matches.
    """
    if not isinstance(html, str) or not html:
        return html, 0

    replaced = 0

    def _sub(match: re.Match) -> str:
        nonlocal replaced
        image = InlineImage(match)
        try:
            image.decode()
        except (binascii.Error, ValueError):
            return match.group(0)
        url = upload(image)
        if not url:
            return match.group(0)
        replaced += 1
        return f'src="{url}"'

    return _INLINE_IMG_RE.sub(_sub, html), replaced
