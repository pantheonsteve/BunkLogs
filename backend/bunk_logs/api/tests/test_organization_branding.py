"""Tests for ``GET /api/v1/organization/branding/`` (TBE Frontend Readiness).

Unauthenticated by design -- sign-in/sign-up pages call this before login,
so coverage focuses on tenant resolution (header) and the branding
fallback chain, not permissions.
"""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from bunk_logs.core.models import Organization

pytestmark = pytest.mark.django_db

URL = "/api/v1/organization/branding/"


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
        "branding": {"display_name": "Temple Beth-El", "product_name": "BunkLogs"},
    }


def test_falls_back_to_org_name_without_branding_settings(api):
    Organization.objects.create(name="No Branding Org", slug="no-branding-test")

    resp = api.get(URL, **_hdr("no-branding-test"))

    assert resp.status_code == 200
    assert resp.data["branding"] == {
        "display_name": "No Branding Org",
        "product_name": "BunkLogs",
    }


def test_unresolved_org_returns_generic_default(api):
    resp = api.get(URL, **_hdr("unknown-slug-does-not-exist"))

    assert resp.status_code == 200
    assert resp.data == {
        "slug": None,
        "name": None,
        "branding": {"display_name": "BunkLogs", "product_name": "BunkLogs"},
    }


def test_no_slug_header_returns_generic_default(api):
    resp = api.get(URL)

    assert resp.status_code == 200
    assert resp.data["slug"] is None
    assert resp.data["branding"]["display_name"] == "BunkLogs"
