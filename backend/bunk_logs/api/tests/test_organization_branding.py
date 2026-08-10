"""Tests for ``GET /api/v1/organization/branding/`` (TBE Frontend Readiness).

Unauthenticated by design -- sign-in/sign-up pages call this before login,
so coverage focuses on tenant resolution (header) and the branding
fallback chain, not permissions.
"""
from __future__ import annotations

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from bunk_logs.core.models import Organization

pytestmark = pytest.mark.django_db

URL = "/api/v1/organization/branding/"

# 1x1 white PNG; passes ImageField validation without a PIL dependency at runtime.
PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff"
    b"?\x00\x05\xfe\x02\xfe\r\xefF\xb8\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _hdr(slug: str) -> dict:
    return {"HTTP_X_ORGANIZATION_SLUG": slug}


@pytest.fixture
def api() -> APIClient:
    return APIClient()


def test_returns_configured_branding_for_resolved_org(api):
    Organization.objects.create(
        name="Temple Beth-El",
        slug="tbe-branding-test",
        settings={"branding": {"display_name": "Temple Beth-El"}},
    )

    resp = api.get(URL, **_hdr("tbe-branding-test"))

    assert resp.status_code == 200
    assert resp.data == {
        "slug": "tbe-branding-test",
        "name": "Temple Beth-El",
        "branding": {
            "display_name": "Temple Beth-El",
            "product_name": "BunkLogs",
            "logo_url": None,
            "hero_url": None,
        },
    }


def test_returns_uploaded_logo_and_hero_urls(api):
    org = Organization.objects.create(
        name="Branded Org",
        slug="branded-org-test",
        settings={"branding": {"display_name": "Branded Org"}},
    )
    org.logo.save("logo.png", SimpleUploadedFile("logo.png", PNG_BYTES, content_type="image/png"))
    org.login_hero.save(
        "hero.png",
        SimpleUploadedFile("hero.png", PNG_BYTES, content_type="image/png"),
    )
    org.refresh_from_db()

    resp = api.get(URL, **_hdr("branded-org-test"))

    assert resp.status_code == 200
    branding = resp.data["branding"]
    assert branding["display_name"] == "Branded Org"
    assert branding["logo_url"] is not None
    assert branding["hero_url"] is not None
    assert branding["logo_url"].startswith("http://")
    assert "/branding/branded-org-test/logo.png" in branding["logo_url"]
    assert f"v={int(org.updated_at.timestamp())}" in branding["logo_url"]
    assert f"v={int(org.updated_at.timestamp())}" in branding["hero_url"]


def test_falls_back_to_org_name_without_branding_settings(api):
    Organization.objects.create(name="No Branding Org", slug="no-branding-test")

    resp = api.get(URL, **_hdr("no-branding-test"))

    assert resp.status_code == 200
    assert resp.data["branding"] == {
        "display_name": "No Branding Org",
        "product_name": "BunkLogs",
        "logo_url": None,
        "hero_url": None,
    }


def test_unresolved_org_returns_generic_default(api):
    resp = api.get(URL, **_hdr("unknown-slug-does-not-exist"))

    assert resp.status_code == 200
    assert resp.data == {
        "slug": None,
        "name": None,
        "branding": {
            "display_name": "BunkLogs",
            "product_name": "BunkLogs",
            "logo_url": None,
            "hero_url": None,
        },
    }


def test_no_slug_header_returns_generic_default(api):
    resp = api.get(URL)

    assert resp.status_code == 200
    assert resp.data["slug"] is None
    assert resp.data["branding"]["display_name"] == "BunkLogs"
    assert resp.data["branding"]["logo_url"] is None
