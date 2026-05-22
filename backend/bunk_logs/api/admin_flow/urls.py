"""URL patterns for the Admin Flow namespace.

Mounted at ``/api/v1/admin/`` from :mod:`bunk_logs.api.urls`.
"""

from __future__ import annotations

from django.urls import path

from bunk_logs.api.audit import AuditEventViewSet

from .dashboard import AdminDashboardView
from .override import AdminOverrideEditView

# Reuse the existing AuditEventViewSet so /admin/audit/ shares the
# audit-view meta-event and pagination behaviour with /audit/. The
# admin-flow path is the canonical one for Story 59; the bare /audit/
# path stays for backward compatibility with existing PRs that already
# wire to it.
_audit_list = AuditEventViewSet.as_view({"get": "list"})
_audit_by_actor = AuditEventViewSet.as_view({"get": "by_actor"})
_audit_admin_overrides = AuditEventViewSet.as_view({"get": "admin_overrides"})


urlpatterns = [
    path("dashboard/", AdminDashboardView.as_view(), name="admin-dashboard"),
    path("override-edit/", AdminOverrideEditView.as_view(), name="admin-override-edit"),
    path("audit/", _audit_list, name="admin-audit"),
    path("audit/by-actor/", _audit_by_actor, name="admin-audit-by-actor"),
    path("audit/admin-overrides/", _audit_admin_overrides, name="admin-audit-admin-overrides"),
]
