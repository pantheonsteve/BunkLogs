"""Tenant-aware frontend URLs for allauth headless account emails.

HEADLESS_FRONTEND_URLS is a single default host. Account emails must use
the SPA origin that requested them so each organization gets its own link.
"""

from __future__ import annotations

from urllib.parse import urlparse
from urllib.parse import urlunparse

from allauth.headless.adapter import DefaultHeadlessAdapter

from bunk_logs.users.frontend_origins import origin_for_account_email


def replace_origin(url: str, origin: str) -> str:
    parsed = urlparse(url)
    new = urlparse(origin)
    if not parsed.netloc or not new.netloc:
        return url
    return urlunparse(parsed._replace(scheme=new.scheme, netloc=new.netloc))


class HeadlessAdapter(DefaultHeadlessAdapter):
    """Rewrite headless frontend URLs onto the requesting tenant's host."""

    def get_frontend_url(self, urlname, **kwargs):
        url = super().get_frontend_url(urlname, **kwargs)
        if not url:
            return url
        return replace_origin(url, origin_for_account_email(self.request))
