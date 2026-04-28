"""
config/api_router.py — redirect shim only.

All data endpoints have been consolidated under /api/v1/ (bunk_logs/api/urls.py).
This module keeps the old /api/<resource>/ paths alive as 302 redirects so that
any bookmark or cached call still resolves, but the canonical URL is /api/v1/*.

Once all callers (frontend + any external integrations) have been confirmed to
use /api/v1/ exclusively, this file can be replaced with an empty urlpatterns=[].
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

    # --- Bunks ---
    path("bunks/", _r("bunks/"), name="redirect-bunks-list"),
    re_path(r"^bunks/(?P<pk>[^/]+)/$", _r("bunks/{pk}/"), name="redirect-bunks-detail"),
    re_path(r"^bunk/(?P<id>[^/]+)/$", _r("bunk/{id}/"), name="redirect-bunk-detail-alt"),

    # --- Units ---
    path("units/", _r("units/"), name="redirect-units-list"),
    re_path(r"^units/(?P<pk>[^/]+)/$", _r("units/{pk}/"), name="redirect-units-detail"),

    # --- Unit staff assignments ---
    path("unit-staff-assignments/", _r("unit-staff-assignments/"), name="redirect-usa-list"),
    re_path(r"^unit-staff-assignments/(?P<pk>[^/]+)/$", _r("unit-staff-assignments/{pk}/"), name="redirect-usa-detail"),

    # --- Campers ---
    path("campers/", _r("campers/"), name="redirect-campers-list"),
    re_path(r"^campers/(?P<pk>[^/]+)/$", _r("campers/{pk}/"), name="redirect-campers-detail"),
    re_path(r"^campers/(?P<camper_id>[^/]+)/logs/$", _r("campers/{camper_id}/logs/"), name="redirect-camper-logs"),

    # --- Camper bunk assignments ---
    path("camper-bunk-assignments/", _r("camper-bunk-assignments/"), name="redirect-cba-list"),
    re_path(r"^camper-bunk-assignments/(?P<pk>[^/]+)/$", _r("camper-bunk-assignments/{pk}/"), name="redirect-cba-detail"),

    # --- Bunk logs ---
    path("bunk-logs/", _r("bunklogs/"), name="redirect-bunk-logs-list"),
    re_path(r"^bunk-logs/(?P<pk>[^/]+)/$", _r("bunklogs/{pk}/"), name="redirect-bunk-logs-detail"),
    re_path(r"^bunklogs/all/(?P<date>[^/]+)/$", _r("bunklogs/all/{date}/"), name="redirect-bunklogs-all"),
    re_path(r"^bunklogs/(?P<bunk_id>[^/]+)/logs/(?P<date>[^/]+)/$", _r("bunklogs/{bunk_id}/logs/{date}/"), name="redirect-bunklogs-by-date"),

    # --- Counselor logs ---
    path("counselor-logs/", _r("counselorlogs/"), name="redirect-counselor-logs-list"),
    re_path(r"^counselor-logs/(?P<pk>[^/]+)/$", _r("counselorlogs/{pk}/"), name="redirect-counselor-logs-detail"),

    # --- Orders (previously only on /api/, now on /api/v1/) ---
    path("orders/", _r("orders/"), name="redirect-orders-list"),
    path("orders/statistics/", _r("orders/statistics/"), name="redirect-orders-stats"),
    re_path(r"^orders/(?P<pk>[^/]+)/$", _r("orders/{pk}/"), name="redirect-orders-detail"),

    # --- Items ---
    path("items/", _r("items/"), name="redirect-items-list"),
    re_path(r"^items/(?P<pk>[^/]+)/$", _r("items/{pk}/"), name="redirect-items-detail"),

    # --- Item categories ---
    path("item-categories/", _r("item-categories/"), name="redirect-item-cats-list"),
    re_path(r"^item-categories/(?P<pk>[^/]+)/$", _r("item-categories/{pk}/"), name="redirect-item-cats-detail"),

    # --- Order types ---
    path("order-types/", _r("order-types/"), name="redirect-order-types-list"),
    re_path(r"^order-types/(?P<pk>[^/]+)/$", _r("order-types/{pk}/"), name="redirect-order-types-detail"),
    re_path(r"^order-types/(?P<order_type_id>[^/]+)/items/$", _r("order-types/{order_type_id}/items/"), name="redirect-order-type-items"),

    # --- Messaging ---
    re_path(r"^messaging/(?P<rest>.*)$", _r("messaging/{rest}"), name="redirect-messaging"),

    # --- Unit head / camper care dashboards ---
    re_path(r"^unithead/(?P<unithead_id>[^/]+)/(?P<date>[^/]+)/$", _r("unithead/{unithead_id}/{date}/"), name="redirect-unithead"),
    re_path(r"^campercare/(?P<camper_care_id>[^/]+)/(?P<date>[^/]+)/$", _r("campercare/{camper_care_id}/{date}/"), name="redirect-campercare"),
]
