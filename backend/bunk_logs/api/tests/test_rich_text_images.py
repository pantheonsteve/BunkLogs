"""Tests for rich-text image upload, the inline-base64 guard, and cleanup.

Covers the S3-backed replacement for base64-in-HTML images:
  - the upload endpoint (happy path, auth required, rejects non-images)
  - serializer guards rejecting new inline base64 submissions
  - the migrate_inline_images command extracting existing blobs
"""

import base64
import io
from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient

from bunk_logs.bunklogs.models import StaffLog
from bunk_logs.core.models import RichTextImage
from bunk_logs.core.rich_text import contains_inline_base64_image
from bunk_logs.core.rich_text import replace_inline_images
from bunk_logs.users.tests.factories import UserFactory


def _png_bytes(size=(20, 20), color=(255, 0, 0)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def _data_uri(png=None):
    raw = png or _png_bytes()
    b64 = base64.b64encode(raw).decode()
    return f"data:image/png;base64,{b64}"


class TestRichTextImageUpload(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("api:rich-text-image-upload")
        self.user = UserFactory(counselor=True)

    def test_authenticated_user_can_upload_image(self):
        self.client.force_authenticate(user=self.user)
        upload = SimpleUploadedFile("photo.png", _png_bytes(), content_type="image/png")
        response = self.client.post(self.url, {"image": upload}, format="multipart")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["url"]
        assert RichTextImage.objects.count() == 1
        assert RichTextImage.objects.first().uploaded_by == self.user

    def test_upload_requires_authentication(self):
        upload = SimpleUploadedFile("photo.png", _png_bytes(), content_type="image/png")
        response = self.client.post(self.url, {"image": upload}, format="multipart")
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )
        assert RichTextImage.objects.count() == 0

    def test_upload_rejects_non_image(self):
        self.client.force_authenticate(user=self.user)
        bogus = SimpleUploadedFile("evil.txt", b"not an image", content_type="text/plain")
        response = self.client.post(self.url, {"image": bogus}, format="multipart")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert RichTextImage.objects.count() == 0


class TestReplaceInlineImages(TestCase):
    def test_replace_rewrites_src_and_counts(self):
        html = f'<p>a<img src="{_data_uri()}">b</p>'
        new_html, n = replace_inline_images(html, lambda img: "https://cdn/x.png")
        assert n == 1
        assert "data:image" not in new_html
        assert 'src="https://cdn/x.png"' in new_html

    def test_replace_is_idempotent_on_clean_html(self):
        html = "<p>no images here</p>"
        new_html, n = replace_inline_images(html, lambda img: "https://cdn/x.png")
        assert n == 0
        assert new_html == html


class TestMigrateInlineImagesCommand(TestCase):
    def setUp(self):
        self.user = UserFactory(counselor=True)

    def _make_log_with_inline_image(self):
        return StaffLog.objects.create(
            staff_member=self.user,
            date=date.today(),
            day_quality_score=4,
            support_level_score=4,
            elaboration=f'<p><img src="{_data_uri()}"></p>',
            values_reflection="Plain text.",
        )

    def test_dry_run_does_not_modify(self):
        log = self._make_log_with_inline_image()
        call_command("migrate_inline_images")
        log.refresh_from_db()
        assert contains_inline_base64_image(log.elaboration)
        assert RichTextImage.objects.count() == 0

    def test_commit_extracts_and_rewrites(self):
        log = self._make_log_with_inline_image()
        call_command("migrate_inline_images", "--commit")
        log.refresh_from_db()
        assert not contains_inline_base64_image(log.elaboration)
        assert RichTextImage.objects.count() == 1
        # Second run is a no-op (idempotent).
        call_command("migrate_inline_images", "--commit")
        assert RichTextImage.objects.count() == 1
