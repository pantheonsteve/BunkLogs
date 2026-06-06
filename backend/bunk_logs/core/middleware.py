from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import SuspiciousOperation

from bunk_logs.core.context import clear_current_organization
from bunk_logs.core.context import set_current_organization

if TYPE_CHECKING:
    from django.http import HttpRequest
    from django.http import HttpResponse

    from bunk_logs.core.models import Organization

# First label of host must match Organization.slug (e.g. clc.bunklogs.net → slug "clc").
_SUBDOMAIN_SKIP = frozenset({"", "www", "admin", "api", "localhost"})


def _raw_request_host(request: HttpRequest) -> str:
    """Host from META when get_host() rejects the client (e.g. tests, misconfigured ALLOWED_HOSTS)."""
    raw = request.META.get("HTTP_HOST", "")
    return raw.split(":")[0] if raw else ""


def _request_host_for_tenant(request: HttpRequest) -> str:
    try:
        return request.get_host().split(":")[0].lower()
    except SuspiciousOperation:
        return _raw_request_host(request)


def _dev_org_routing_overrides_enabled() -> bool:
    return bool(settings.DEBUG) or bool(
        getattr(settings, "ORGANIZATION_ROUTING_DEV_OVERRIDES", False),
    )


def _org_slug_from_header(request: HttpRequest) -> str | None:
    """Tenant slug from X-Organization-Slug (SPA → admin API calls)."""
    header = (request.META.get("HTTP_X_ORGANIZATION_SLUG") or "").strip()
    return header or None


def _org_slug_from_query_dev_only(request: HttpRequest) -> str | None:
    if not _dev_org_routing_overrides_enabled():
        return None
    q = (request.GET.get("org") or "").strip()
    return q or None


def _org_slug_override(request: HttpRequest) -> str | None:
    return _org_slug_from_header(request) or _org_slug_from_query_dev_only(request)


def _user_from_bearer_jwt(request: HttpRequest):
    """Resolve user from Authorization: Bearer for org fallback before DRF runs."""
    auth = (request.META.get("HTTP_AUTHORIZATION") or "").strip()
    if not auth.lower().startswith("bearer "):
        return None
    from rest_framework_simplejwt.authentication import JWTAuthentication

    try:
        result = JWTAuthentication().authenticate(request)
    except Exception:
        return None
    if result is None:
        return None
    user, _token = result
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    return user


def _org_from_linked_person(user) -> Organization | None:
    from bunk_logs.core.models import Person

    person = (
        Person.all_objects.select_related("organization")
        .filter(user=user)
        .first()
    )
    if person is None:
        return None
    org = person.organization
    return org if org.is_active else None


def _host_subdomain_label(host: str) -> str | None:
    host = host.lower().strip(".")
    parts = host.split(".")
    if len(parts) < 3:
        return None
    # e.g. clc.bunklogs.net → clc
    if parts[-2:] != ["bunklogs", "net"]:
        return None
    label = parts[0]
    if label in _SUBDOMAIN_SKIP:
        return None
    return label


class OrganizationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        from bunk_logs.core.models import Organization

        org: Organization | None = None
        try:
            label = _host_subdomain_label(_request_host_for_tenant(request))
            if label:
                try:
                    org = Organization.objects.get(slug=label, is_active=True)
                except ObjectDoesNotExist:
                    org = None

            if org is None:
                slug = _org_slug_override(request)
                if slug:
                    try:
                        org = Organization.objects.get(slug=slug, is_active=True)
                    except ObjectDoesNotExist:
                        org = None

            user = getattr(request, "user", None)
            if user is not None and user.is_authenticated:
                effective_user = user
            else:
                effective_user = _user_from_bearer_jwt(request)

            if org is None and effective_user is not None:
                org = _org_from_linked_person(effective_user)

            request.organization = org
            set_current_organization(org)
            return self.get_response(request)
        finally:
            clear_current_organization()
