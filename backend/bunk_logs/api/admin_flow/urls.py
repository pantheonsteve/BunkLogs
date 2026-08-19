"""URL patterns for the Admin Flow namespace.

Mounted at ``/api/v1/admin/`` from :mod:`bunk_logs.api.urls`.
"""

from __future__ import annotations

from django.urls import path

from bunk_logs.api.audit import AuditEventViewSet

from .assignments import AdminAssignmentDetailView
from .assignments import AdminAssignmentsListCreateView
from .assignments import AdminSupervisorStatusView
from .catalog import AdminCatalogImportView
from .catalog import AdminCatalogItemDetailView
from .catalog import AdminCatalogItemListCreateView
from .catalog import AdminCatalogTemplateView
from .catalog import AdminCatalogTreeView
from .catalog import AdminRequestTypeDetailView
from .catalog import AdminRequestTypeListCreateView
from .catalog import AdminStoreDetailView
from .catalog import AdminStoreListCreateView
from .catalog_dashboard import AdminCatalogPlanningView
from .classroom_challenges import AdminClassroomChallengesExportView
from .classroom_challenges import AdminClassroomChallengesListView
from .dashboard import AdminDashboardView
from .director import DirectorCoverageDetailView
from .director import DirectorCoverageView
from .director import DirectorFacultyActivityView
from .director import DirectorMadrichimExportView
from .director import DirectorMadrichimView
from .director import DirectorPulseView
from .director import DirectorQueueView
from .director import DirectorThemesView
from .growth import AdminGrowthDashboardExportView
from .growth import AdminGrowthDashboardView
from .growth import AdminGrowthExamplesView
from .imports import AdminBulkImportCommitView
from .imports import AdminBulkImportPreviewView
from .imports import AdminBulkImportTemplateView
from .madrich_availability import AdminMadrichAvailabilityExportView
from .madrich_availability import AdminMadrichAvailabilityView
from .override import AdminOverrideEditView
from .people import AdminMembershipDeactivateView
from .people import AdminMembershipDetailView
from .people import AdminPeopleDetailView
from .people import AdminPeopleListCreateView
from .people import AdminPersonInviteView
from .people import AdminPersonMembershipsView
from .people_dedupe import AdminPeopleDedupeApplyView
from .people_dedupe import AdminPeopleDedupePreviewView
from .people_delete import AdminPersonDeleteApplyView
from .people_delete import AdminPersonDeletePreviewView
from .programs import AdminMaintenanceNotificationsTestView
from .programs import AdminProgramDetailView
from .programs import AdminProgramEndView
from .programs import AdminProgramsListCreateView
from .programs import AdminSettingsView
from .reflections import AdminReflectionsMemberDetailView
from .reflections import AdminReflectionsTeamExportView
from .reflections import AdminReflectionsTeamView
from .search import AdminGlobalSearchView
from .templates import AdminTemplateReviewView
from .templates import AdminTemplatesListView

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
        "people/dedupe/preview/",
        AdminPeopleDedupePreviewView.as_view(),
        name="admin-people-dedupe-preview",
    ),
    path(
        "people/dedupe/",
        AdminPeopleDedupeApplyView.as_view(),
        name="admin-people-dedupe",
    ),
    path(
        "people/<int:person_id>/delete/preview/",
        AdminPersonDeletePreviewView.as_view(),
        name="admin-person-delete-preview",
    ),
    path(
        "people/<int:person_id>/delete/",
        AdminPersonDeleteApplyView.as_view(),
        name="admin-person-delete",
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
        "assignments/supervisor-status/",
        AdminSupervisorStatusView.as_view(),
        name="admin-assignment-supervisor-status",
    ),
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
    path(
        "settings/test-notifications/",
        AdminMaintenanceNotificationsTestView.as_view(),
        name="admin-settings-test-notifications",
    ),
    # ------------------------------------------------------------------
    # Global search + Templates oversight + Bulk import (PR3)
    # ------------------------------------------------------------------
    path("search/", AdminGlobalSearchView.as_view(), name="admin-search"),
    path("templates/", AdminTemplatesListView.as_view(), name="admin-templates"),
    path(
        "templates/<int:template_id>/review/",
        AdminTemplateReviewView.as_view(),
        name="admin-template-review",
    ),
    path(
        "people/import/preview/",
        AdminBulkImportPreviewView.as_view(),
        name="admin-people-import-preview",
    ),
    path(
        "people/import/template/",
        AdminBulkImportTemplateView.as_view(),
        name="admin-people-import-template",
    ),
    path(
        "people/import/commit/",
        AdminBulkImportCommitView.as_view(),
        name="admin-people-import-commit",
    ),
    # ------------------------------------------------------------------
    # Configurable catalog (Store / RequestType / CatalogItem)
    # ------------------------------------------------------------------
    path("catalog/tree/", AdminCatalogTreeView.as_view(), name="admin-catalog-tree"),
    path("catalog/stores/", AdminStoreListCreateView.as_view(), name="admin-catalog-stores"),
    path(
        "catalog/stores/<int:store_id>/",
        AdminStoreDetailView.as_view(),
        name="admin-catalog-store-detail",
    ),
    path(
        "catalog/request-types/",
        AdminRequestTypeListCreateView.as_view(),
        name="admin-catalog-request-types",
    ),
    path(
        "catalog/request-types/<int:type_id>/",
        AdminRequestTypeDetailView.as_view(),
        name="admin-catalog-request-type-detail",
    ),
    path("catalog/items/", AdminCatalogItemListCreateView.as_view(), name="admin-catalog-items"),
    path(
        "catalog/items/<int:item_id>/",
        AdminCatalogItemDetailView.as_view(),
        name="admin-catalog-item-detail",
    ),
    path("catalog/template.csv", AdminCatalogTemplateView.as_view(), name="admin-catalog-template"),
    path("catalog/import/", AdminCatalogImportView.as_view(), name="admin-catalog-import"),
    path(
        "catalog/planning/",
        AdminCatalogPlanningView.as_view(),
        name="admin-catalog-planning",
    ),
    # ------------------------------------------------------------------
    # Reflections completion dashboard (Step 4_4 — TBE)
    # ------------------------------------------------------------------
    path(
        "reflections/teams/<str:role>/",
        AdminReflectionsTeamView.as_view(),
        name="admin-reflections-team",
    ),
    path(
        "reflections/teams/<str:role>/export/",
        AdminReflectionsTeamExportView.as_view(),
        name="admin-reflections-team-export",
    ),
    path(
        "reflections/teams/<str:role>/members/<int:membership_id>/",
        AdminReflectionsMemberDetailView.as_view(),
        name="admin-reflections-member-detail",
    ),
    # ------------------------------------------------------------------
    # Growth dashboard by grade level
    # ------------------------------------------------------------------
    path(
        "reflections/growth/",
        AdminGrowthDashboardView.as_view(),
        name="admin-reflections-growth",
    ),
    path(
        "reflections/growth/export/",
        AdminGrowthDashboardExportView.as_view(),
        name="admin-reflections-growth-export",
    ),
    path(
        "reflections/growth/examples/",
        AdminGrowthExamplesView.as_view(),
        name="admin-reflections-growth-examples",
    ),
    # ------------------------------------------------------------------
    # Director homepage (Step 4_9 — TBE). "Director" is the admin
    # capability in a religious-school program, not a separate role.
    # ------------------------------------------------------------------
    path(
        "reflections/pulse/",
        DirectorPulseView.as_view(),
        name="admin-reflections-pulse",
    ),
    path(
        "reflections/queue/",
        DirectorQueueView.as_view(),
        name="admin-reflections-queue",
    ),
    path(
        "reflections/coverage/",
        DirectorCoverageView.as_view(),
        name="admin-reflections-coverage",
    ),
    path(
        "reflections/coverage/<str:session_date>/",
        DirectorCoverageDetailView.as_view(),
        name="admin-reflections-coverage-detail",
    ),
    path(
        "reflections/faculty-activity/",
        DirectorFacultyActivityView.as_view(),
        name="admin-reflections-faculty-activity",
    ),
    path(
        "reflections/themes/",
        DirectorThemesView.as_view(),
        name="admin-reflections-themes",
    ),
    path(
        "reflections/madrichim/",
        DirectorMadrichimView.as_view(),
        name="admin-reflections-madrichim",
    ),
    path(
        "reflections/madrichim/export/",
        DirectorMadrichimExportView.as_view(),
        name="admin-reflections-madrichim-export",
    ),
    # ------------------------------------------------------------------
    # Madrich availability staffing matrix (Step 4_7 — TBE)
    # ------------------------------------------------------------------
    path(
        "madrich-availability/",
        AdminMadrichAvailabilityView.as_view(),
        name="admin-madrich-availability",
    ),
    path(
        "madrich-availability/export.csv",
        AdminMadrichAvailabilityExportView.as_view(),
        name="admin-madrich-availability-export",
    ),
    # ------------------------------------------------------------------
    # Classroom Challenge Log oversight (Step 4_8 — TBE)
    # ------------------------------------------------------------------
    path(
        "classroom-challenges/",
        AdminClassroomChallengesListView.as_view(),
        name="admin-classroom-challenges",
    ),
    path(
        "classroom-challenges/export.csv",
        AdminClassroomChallengesExportView.as_view(),
        name="admin-classroom-challenges-export",
    ),
]
