"""Public organization identity endpoint (TBE Frontend Readiness).

Exposes the minimal branding info the frontend needs to render before a
user is authenticated (sign-in / sign-up / password reset pages). Tenant
resolution reuses ``OrganizationMiddleware`` -- it already sets
``request.organization`` from the Host header or ``X-Organization-Slug``
override for every request, auth or not -- so this view is a thin read
over that, not a second tenancy mechanism.

Deliberately narrow: only display-oriented keys from
``Organization.settings["branding"]`` plus uploaded image URLs are
returned, never the full ``settings`` blob, since that also holds
operational config (reminder schedules, maintenance recipients, etc.)
that shouldn't be public.

``terminology`` rides along for the same reason branding does -- the app
shell needs the tenant's nouns before login resolves. It is display-only
(see ``core.terminology``) and leaks nothing an unauthenticated visitor
can't already read off the sign-in page.
"""
from __future__ import annotations

from typing import Any

from rest_framework.decorators import api_view
from rest_framework.decorators import permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from bunk_logs.core.terminology import terms_for_organization

DEFAULT_BRANDING: dict[str, str | None] = {
    "display_name": "BunkLogs",
    "product_name": "BunkLogs",
    "logo_url": None,
    "hero_url": None,
}


def _public_media_url(request, field_file, *, version: int) -> str | None:
    """Return an absolute, cache-busted URL for a public media file."""
    if not field_file:
        return None
    url = field_file.url
    if url.startswith("/"):
        url = request.build_absolute_uri(url)
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}v={version}"


def _branding_for_organization(org, request) -> dict[str, str | None]:
    configured = (org.settings or {}).get("branding") or {}
    version = int(org.updated_at.timestamp()) if org.updated_at else 0
    branding: dict[str, str | None] = {
        "display_name": configured.get("display_name") or org.name,
        "product_name": configured.get("product_name") or DEFAULT_BRANDING["product_name"],
        "logo_url": _public_media_url(request, org.logo, version=version),
        "hero_url": _public_media_url(request, org.login_hero, version=version),
    }
    return branding


@api_view(["GET"])
@permission_classes([AllowAny])
def branding(request) -> Response:
    """``GET /api/v1/organization/branding/`` -- current tenant's display branding."""
    org = getattr(request, "organization", None)
    if org is None:
        payload: dict[str, Any] = {
            "slug": None,
            "name": None,
            "branding": dict(DEFAULT_BRANDING),
            "terminology": terms_for_organization(None),
        }
        return Response(payload)

    payload = {
        "slug": org.slug,
        "name": org.name,
        "branding": _branding_for_organization(org, request),
        "terminology": terms_for_organization(org),
    }
    return Response(payload)
