"""Storage backends for rich-text inline images.

Rich-text editor images are embedded directly in stored HTML (e.g.
``<img src="https://...">``) and rendered forever, so their URLs must be
*stable* -- they cannot be short-lived presigned URLs like the maintenance
ticket photos use. In production we therefore serve them from S3 with
``querystring_auth=False`` (plain, non-expiring object URLs) under a dedicated
``rich-text/`` prefix that the bucket policy exposes for public read. Keys are
random UUIDs, so URLs are unguessable and not enumerable.

Locally / in tests there is no S3, so we fall back to the default storage
(filesystem under ``MEDIA_ROOT``); the upload view converts that relative
``/media/`` path into an absolute URL before embedding it.
"""

from __future__ import annotations

from django.conf import settings
from django.core.files.storage import default_storage


def select_public_media_storage():
    """Return the storage used for publicly-served rich-text images.

    Passed as a callable to ``ImageField(storage=...)`` so migrations record a
    reference to this function rather than baking S3 credentials into the
    migration graph, and so the S3 vs filesystem choice is resolved lazily at
    runtime from settings.
    """
    if getattr(settings, "RICH_TEXT_USE_S3", False):
        from storages.backends.s3 import S3Storage

        return S3Storage(
            bucket_name=settings.AWS_STORAGE_BUCKET_NAME,
            region_name=getattr(settings, "AWS_S3_REGION_NAME", "us-east-1"),
            # Stable, non-expiring URLs -- these end up inside stored HTML.
            querystring_auth=False,
            # Bucket-owner-enforced (ACLs disabled); public read for the
            # ``rich-text/`` prefix is granted via bucket policy, not per-object ACL.
            default_acl=None,
            file_overwrite=False,
        )
    return default_storage
