"""
config/api_router.py — redirect shim only.

All data endpoints have been consolidated under /api/v1/ (bunk_logs/api/urls.py).
This module keeps a few old /api/<resource>/ paths alive as 302 redirects so
that any bookmark or cached call still resolves, but the canonical URL is
/api/v1/*. Redirects for the removed legacy single-tenant endpoints (bunks,
campers, bunk logs, orders, ...) were dropped along with the endpoints.
"""

from django.http import HttpResponseRedirect
from django.urls import path
from django.urls import re_path


def _r(v1_path):
    """Return a redirect view function targeting /api/v1/<v1_path>."""
    def view(request, **kwargs):
        target = f"/api/v1/{v1_path.format(**kwargs)}"
        qs = request.META.get("QUERY_STRING", "")
        if qs:
            target = f"{target}?{qs}"
        return HttpResponseRedirect(target)
    return view


urlpatterns = [
    # --- Users ---
    path("users/", _r("users/"), name="redirect-users-list"),
    re_path(r"^users/(?P<pk>[^/]+)/$", _r("users/{pk}/"), name="redirect-users-detail"),
    path("users/me/", _r("users/me/"), name="redirect-users-me"),
    re_path(r"^users/email/(?P<email>[^/]+)/$", _r("users/email/{email}/"), name="redirect-users-by-email"),

    # --- Messaging ---
    re_path(r"^messaging/(?P<rest>.*)$", _r("messaging/{rest}"), name="redirect-messaging"),
]
