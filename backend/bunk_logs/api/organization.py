"""Public organization identity endpoint (TBE Frontend Readiness).

Exposes the minimal branding info the frontend needs to render before a
user is authenticated (sign-in / sign-up / password reset pages). Tenant
resolution reuses ``OrganizationMiddleware`` -- it already sets
``request.organization`` from the Host header or ``X-Organization-Slug``
override for every request, auth or not -- so this view is a thin read
over that, not a second tenancy mechanism.

Deliberately narrow: only ``display_name`` and ``product_name`` are
returned (from ``Organization.settings["branding"]``), never the full
``settings`` blob, since that also holds operational config (reminder
schedules, maintenance recipients, etc.) that shouldn't be public.
"""
from __future__ import annotations

from typing import Any

from rest_framework.decorators import api_view
from rest_framework.decorators import permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

DEFAULT_BRANDING: dict[str, str] = {
    "display_name": "BunkLogs",
    "product_name": "BunkLogs",
}


def _branding_for_organization(org) -> dict[str, str]:
    configured = (org.settings or {}).get("branding") or {}
    return {
        "display_name": configured.get("display_name") or org.name,
        "product_name": configured.get("product_name") or DEFAULT_BRANDING["product_name"],
    }


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
        }
        return Response(payload)

    payload = {
        "slug": org.slug,
        "name": org.name,
        "branding": _branding_for_organization(org),
    }
    return Response(payload)
