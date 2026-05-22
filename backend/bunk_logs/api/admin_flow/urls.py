"""URL patterns for the Admin Flow namespace.

Mounted at ``/api/v1/admin/`` from :mod:`bunk_logs.api.urls`.
"""

from __future__ import annotations

from django.urls import path

from bunk_logs.api.audit import AuditEventViewSet

from .assignments import AdminAssignmentDetailView
from .assignments import AdminAssignmentsListCreateView
from .dashboard import AdminDashboardView
from .override import AdminOverrideEditView
from .people import AdminMembershipDeactivateView
from .people import AdminMembershipDetailView
from .people import AdminPeopleDetailView
from .people import AdminPeopleListCreateView
from .people import AdminPersonInviteView
from .people import AdminPersonMembershipsView
from .programs import AdminProgramDetailView
from .programs import AdminProgramEndView
from .programs import AdminProgramsListCreateView
from .programs import AdminSettingsView

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
    # ------------------------------------------------------------------
    # People + Memberships (Story 55)
    # ------------------------------------------------------------------
    path("people/", AdminPeopleListCreateView.as_view(), name="admin-people"),
    path("people/<int:person_id>/", AdminPeopleDetailView.as_view(), name="admin-person-detail"),
    path(
        "people/<int:person_id>/memberships/",
        AdminPersonMembershipsView.as_view(),
        name="admin-person-memberships",
    ),
    path(
        "people/<int:person_id>/invite/",
        AdminPersonInviteView.as_view(),
        name="admin-person-invite",
    ),
    path(
        "memberships/<int:membership_id>/",
        AdminMembershipDetailView.as_view(),
        name="admin-membership-detail",
    ),
    path(
        "memberships/<int:membership_id>/deactivate/",
        AdminMembershipDeactivateView.as_view(),
        name="admin-membership-deactivate",
    ),
    # ------------------------------------------------------------------
    # Assignments (Story 56) — single endpoint, 5 sub-tabs
    # ------------------------------------------------------------------
    path("assignments/", AdminAssignmentsListCreateView.as_view(), name="admin-assignments"),
    path(
        "assignments/<int:assignment_id>/",
        AdminAssignmentDetailView.as_view(),
        name="admin-assignment-detail",
    ),
    # ------------------------------------------------------------------
    # Programs + Settings (Story 58)
    # ------------------------------------------------------------------
    path("programs/", AdminProgramsListCreateView.as_view(), name="admin-programs"),
    path(
        "programs/<int:program_id>/",
        AdminProgramDetailView.as_view(),
        name="admin-program-detail",
    ),
    path(
        "programs/<int:program_id>/end/",
        AdminProgramEndView.as_view(),
        name="admin-program-end",
    ),
    path("settings/", AdminSettingsView.as_view(), name="admin-settings"),
]
