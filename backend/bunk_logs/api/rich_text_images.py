"""Rich-text editor image upload endpoint.

``POST /api/v1/rich-text-images/`` (multipart, field ``image``) stores an image
via the public rich-text storage and returns its stable URL, which the editor
embeds as ``<img src="...">``. Replaces the old base64-in-HTML behaviour that
bloated the DB.

Uploads are re-encoded server-side: EXIF orientation is applied then stripped,
oversized images are downscaled, and the result is written as JPEG/PNG. This
caps stored size regardless of what the client sends and drops location EXIF.
"""

from __future__ import annotations

import io

from django.core.files.base import ContentFile
from PIL import Image
from PIL import ImageOps
from PIL import UnidentifiedImageError
from rest_framework import serializers
from rest_framework import status
from rest_framework.parsers import FormParser
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.models import RichTextImage

# Reject oversized uploads before decoding (defense against decompression bombs
# and accidental huge files). 15 MB is generous for a photo.
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
# Longest edge after downscaling. Keeps inline images readable without storing
# full-resolution camera output inside a rich-text field's neighbourhood.
MAX_DIMENSION = 1600
JPEG_QUALITY = 85


class RichTextImageUploadSerializer(serializers.Serializer):
    image = serializers.ImageField()


def process_image(uploaded_file) -> tuple[ContentFile, str]:
    """Downscale + re-encode an uploaded image, returning (content, extension).

    Preserves alpha (PNG in -> PNG out); everything else becomes JPEG. Raises
    ``serializers.ValidationError`` if the file isn't a decodable image.
    """
    try:
        img = Image.open(uploaded_file)
        img = ImageOps.exif_transpose(img)  # bake orientation, drop EXIF
    except (UnidentifiedImageError, OSError) as exc:
        raise serializers.ValidationError({"image": "Not a valid image file."}) from exc

    has_alpha = img.mode in ("RGBA", "LA", "P")
    img.thumbnail((MAX_DIMENSION, MAX_DIMENSION))

    buffer = io.BytesIO()
    if has_alpha:
        img.convert("RGBA").save(buffer, format="PNG", optimize=True)
        ext = ".png"
    else:
        img.convert("RGB").save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        ext = ".jpg"
    buffer.seek(0)
    return ContentFile(buffer.read()), ext


class RichTextImageUploadView(APIView):
    """Upload a single image for embedding in a rich-text field."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    http_method_names = ["post", "head", "options"]

    def post(self, request, *args, **kwargs):
        uploaded = request.FILES.get("image")
        if uploaded is not None and uploaded.size > MAX_UPLOAD_BYTES:
            return Response(
                {"image": "Image is too large (max 15 MB)."},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )

        serializer = RichTextImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        content, ext = process_image(serializer.validated_data["image"])
        image_model = RichTextImage(uploaded_by=request.user)
        image_model.image.save(f"{image_model.id}{ext}", content, save=True)

        # In prod the storage returns an absolute S3 URL; locally it's a
        # ``/media/...`` path that must be absolutised so the frontend (served
        # from a different origin) can load it.
        url = image_model.image.url
        if url.startswith("/"):
            url = request.build_absolute_uri(url)

        return Response({"url": url}, status=status.HTTP_201_CREATED)
