"""Resize/re-encode org branding uploads before storage.

Logos and login heroes are public, long-lived assets embedded on auth
pages. Re-encoding caps stored size and strips EXIF (same rationale as
``api.rich_text_images``).
"""

from __future__ import annotations

import io

from django.core.files.base import ContentFile
from PIL import Image
from PIL import ImageOps
from PIL import UnidentifiedImageError

LOGO_MAX_DIMENSION = 400
HERO_MAX_DIMENSION = 1600
JPEG_QUALITY = 85


def _process_image(uploaded_file, *, max_dimension: int) -> tuple[ContentFile, str]:
    try:
        img = Image.open(uploaded_file)
        img = ImageOps.exif_transpose(img)
    except (UnidentifiedImageError, OSError) as exc:
        msg = "Not a valid image file."
        raise ValueError(msg) from exc

    has_alpha = img.mode in ("RGBA", "LA", "P")
    img.thumbnail((max_dimension, max_dimension))

    buffer = io.BytesIO()
    if has_alpha:
        img.convert("RGBA").save(buffer, format="PNG", optimize=True)
        ext = ".png"
    else:
        img.convert("RGB").save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        ext = ".jpg"
    buffer.seek(0)
    return ContentFile(buffer.read()), ext


def process_branding_logo(uploaded_file) -> tuple[ContentFile, str]:
    return _process_image(uploaded_file, max_dimension=LOGO_MAX_DIMENSION)


def process_branding_hero(uploaded_file) -> tuple[ContentFile, str]:
    return _process_image(uploaded_file, max_dimension=HERO_MAX_DIMENSION)
