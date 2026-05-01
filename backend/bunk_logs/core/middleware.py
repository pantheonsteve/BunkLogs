from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.exceptions import ObjectDoesNotExist

from bunk_logs.core.context import clear_current_organization
from bunk_logs.core.context import set_current_organization

if TYPE_CHECKING:
    from django.http import HttpRequest
    from django.http import HttpResponse

    from bunk_logs.core.models import Organization

# First label of host must match Organization.slug (e.g. clc.bunklogs.net → slug "clc").
_SUBDOMAIN_SKIP = frozenset({"", "www", "admin", "api", "localhost"})


def _raw_request_host(request: HttpRequest) -> str:
    """Host for tenant routing without triggering ALLOWED_HOSTS (see get_host())."""
    raw = request.META.get("HTTP_HOST", "")
    return raw.split(":")[0] if raw else ""


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
        from bunk_logs.core.models import Person

        org: Organization | None = None
        try:
            label = _host_subdomain_label(_raw_request_host(request))
            if label:
                try:
                    org = Organization.objects.get(slug=label, is_active=True)
                except ObjectDoesNotExist:
                    org = None

            user = getattr(request, "user", None)
            if org is None and user is not None and user.is_authenticated:
                person = (
                    Person.all_objects.select_related("organization")
                    .filter(user=user)
                    .first()
                )
                if person is not None:
                    org = person.organization if person.organization.is_active else None

            request.organization = org
            set_current_organization(org)
            return self.get_response(request)
        finally:
            clear_current_organization()
