from django.urls import include
from django.urls import path
from rest_framework.routers import DefaultRouter

from bunk_logs.users.api.views import UserViewSet

from . import assignment_groups
from . import audit as audit_api
from . import field_keys as field_keys_api
from . import me as me_api
from . import memberships
from . import orders_state_machine as order_sm
from . import reflections
from . import supervisions as supervisions_api
from . import templates as templates_api
from . import views
from .camper_care import bunk_dashboard as cc_bunk_dashboard
from .camper_care import camper_dashboard as cc_camper_dashboard
from .camper_care import dashboard as cc_dashboard
from .camper_care import flags as cc_flags
from .camper_care import orders as cc_orders
from .camper_care import self_reflection as cc_self_reflection
from .counselor import camper_care_requests as counselor_camper_care_requests
from .counselor import camper_reflections as counselor_camper_reflections
from .counselor import dashboard as counselor_dashboard
from .counselor import maintenance_tickets as counselor_maintenance_tickets
from .counselor import requests as counselor_requests
from .counselor import self_reflection as counselor_self_reflection
from .dashboards import authors as authors_dashboard
from .dashboards import concerns as concerns_dashboard
from .dashboards import coverage as coverage_dashboard
from .dashboards import group_dashboard as group_dashboard_api
from .dashboards import subject as subject_dashboard
from .dashboards import template as template_dashboard
from .dashboards import trends as trends_dashboard
from .kitchen_staff import dashboard as ks_dashboard
from .kitchen_staff import self_reflection as ks_self_reflection
from .leadership_team import assignments as lt_assignments
from .leadership_team import dashboard as lt_dashboard
from .leadership_team import exports as lt_exports
from .leadership_team import mark_attention as lt_mark_attention
from .leadership_team import member_reflection as lt_member_reflection
from .leadership_team import responses as lt_responses
from .leadership_team import self_reflection as lt_self_reflection
from .leadership_team import team_dashboard as lt_team_dashboard
from .leadership_team import templates as lt_templates
from .madrich import dashboard as md_dashboard
from .madrich import reflection as md_reflection
from .maintenance import views as maint_views
from .observations import views as observations_views
from .specialist import camper_view as sp_camper_view
from .specialist import campers as sp_campers
from .specialist import dashboard as sp_dashboard
from .specialist import self_reflection as sp_self_reflection
from .unit_head import bunk_dashboard as uh_bunk_dashboard
from .unit_head import camper_dashboard as uh_camper_dashboard
from .unit_head import dashboard as uh_dashboard
from .unit_head import self_reflection as uh_self_reflection

router = DefaultRouter()

# Users
router.register(r"users", UserViewSet, basename="user")

# Core bunk logs
router.register(r"bunks", views.BunkViewSet, basename="bunk")
router.register(r"units", views.UnitViewSet, basename="unit")
router.register(r"unit-staff-assignments", views.UnitStaffAssignmentViewSet, basename="unit-staff-assignment")
router.register(r"campers", views.CamperViewSet, basename="camper")
router.register(r"camper-bunk-assignments", views.CamperBunkAssignmentViewSet, basename="camper-bunk-assignment")
router.register(r"bunklogs", views.BunkLogViewSet, basename="bunklog")
router.register(r"counselorlogs", views.CounselorLogViewSet, basename="counselorlog")

router.register(r"reflections", reflections.ReflectionViewSet, basename="reflection")
router.register(r"memberships", memberships.MembershipViewSet, basename="membership")
router.register(r"supervisions", supervisions_api.SupervisionViewSet, basename="supervision")
router.register(r"assignment-groups", assignment_groups.AssignmentGroupViewSet, basename="assignment-group")
router.register(r"templates", templates_api.ReflectionTemplateViewSet, basename="template")
router.register(r"field-keys", field_keys_api.FieldKeyViewSet, basename="field-key")
router.register(r"audit", audit_api.AuditEventViewSet, basename="audit")

# Ordering system
router.register(r"orders", views.OrderViewSet, basename="order")
router.register(r"items", views.ItemViewSet, basename="item")
router.register(r"item-categories", views.ItemCategoryViewSet, basename="item-category")
router.register(r"order-types", views.OrderTypeViewSet, basename="order-type")

urlpatterns = [
    # Order/Ticket state machine endpoints (Step 7_2). UUID-typed paths so they
    # do not collide with the legacy ``/api/v1/orders/<int:pk>/`` viewset above.
    path(
        "orders/bulk-transition/",
        order_sm.OrderBulkTransitionView.as_view(),
        name="cc-orders-bulk-transition",
    ),
    path(
        "orders/<uuid:order_id>/transition/",
        order_sm.OrderTransitionView.as_view(),
        name="cc-orders-transition",
    ),
    path(
        "orders/<uuid:order_id>/correct-last/",
        order_sm.OrderCorrectLastView.as_view(),
        name="cc-orders-correct-last",
    ),
    path(
        "maintenance/bulk-transition/",
        order_sm.MaintenanceTicketBulkTransitionView.as_view(),
        name="maintenance-bulk-transition",
    ),
    path(
        "maintenance/<uuid:ticket_id>/transition/",
        order_sm.MaintenanceTicketTransitionView.as_view(),
        name="maintenance-transition",
    ),
    path(
        "maintenance/<uuid:ticket_id>/correct-last/",
        order_sm.MaintenanceTicketCorrectLastView.as_view(),
        name="maintenance-correct-last",
    ),
    # ------------------------------------------------------------------
    # Kitchen Staff (Step 7_11, Stories 37-44)
    # ------------------------------------------------------------------
    path(
        "kitchen-staff/dashboard/",
        ks_dashboard.KitchenStaffDashboardView.as_view(),
        name="kitchen-staff-dashboard",
    ),
    path(
        "kitchen-staff/reflection/",
        ks_self_reflection.KitchenStaffReflectionCreateView.as_view(),
        name="kitchen-staff-reflection-create",
    ),
    path(
        "kitchen-staff/reflection/history/",
        ks_self_reflection.KitchenStaffReflectionHistoryView.as_view(),
        name="kitchen-staff-reflection-history",
    ),
    path(
        "kitchen-staff/reflection/<int:reflection_id>/",
        ks_self_reflection.KitchenStaffReflectionDetailView.as_view(),
        name="kitchen-staff-reflection-detail",
    ),
    # ------------------------------------------------------------------
    # Madrich — TBE weekly 3-2-1 (Step 7_14, Stories 61-65)
    # ------------------------------------------------------------------
    path(
        "madrich/dashboard/",
        md_dashboard.MadrichDashboardView.as_view(),
        name="madrich-dashboard",
    ),
    path(
        "madrich/reflection/",
        md_reflection.MadrichReflectionCreateView.as_view(),
        name="madrich-reflection-create",
    ),
    path(
        "madrich/reflection/history/",
        md_reflection.MadrichReflectionHistoryView.as_view(),
        name="madrich-reflection-history",
    ),
    path(
        "madrich/reflection/<int:reflection_id>/",
        md_reflection.MadrichReflectionDetailView.as_view(),
        name="madrich-reflection-detail",
    ),
    # ------------------------------------------------------------------
    # Maintenance staff queue (Step 7_10, Stories 30-35)
    # ------------------------------------------------------------------
    path(
        "maintenance/queue/",
        maint_views.MaintenanceQueueView.as_view(),
        name="maintenance-queue",
    ),
    path(
        "maintenance/tickets/<uuid:ticket_id>/",
        maint_views.MaintenanceTicketDetailView.as_view(),
        name="maintenance-ticket-detail",
    ),
    path(
        "maintenance/tickets/<uuid:ticket_id>/notes/",
        maint_views.MaintenanceNoteCreateView.as_view(),
        name="maintenance-note-create",
    ),
    path(
        "maintenance/tickets/<uuid:ticket_id>/notes/<uuid:note_id>/",
        maint_views.MaintenanceNoteDetailView.as_view(),
        name="maintenance-note-detail",
    ),
    path(
        "maintenance/notes/audience/",
        maint_views.MaintenanceNoteAudienceView.as_view(),
        name="maintenance-note-audience",
    ),
    path(
        "maintenance/tickets/<uuid:ticket_id>/photos/",
        maint_views.MaintenanceTicketPhotoCreateView.as_view(),
        name="maintenance-ticket-photo-create",
    ),
    path("", include(router.urls)),

    # Step 7_13 — Admin Flow namespace (mounted under /api/v1/admin/).
    # See bunk_logs/api/admin_flow/__init__.py for the package layout.
    path("admin/", include("bunk_logs.api.admin_flow.urls")),

    # Non-standard bunk detail path used by BunkCard.jsx — kept for compat while
    # callers are migrated to the standard /bunks/{id}/ route
    path("bunk/<str:id>/", views.BunkViewSet.as_view({"get": "retrieve"}), name="bunk-detail-compat"),

    # User registration (public)
    path("users/create/", views.UserCreate.as_view(), name="user-create"),

    # Per-user i18n preferences (Step 7_5)
    path("me/preferences/", me_api.MePreferencesView.as_view(), name="me-preferences"),

    # User lookup by email (used by several frontend components)
    path("users/email/<str:email>/", views.get_user_by_email, name="user-by-email"),

    # Messaging system
    path("messaging/", include("bunk_logs.messaging.urls")),

    # Ordering system helpers
    path("order-types/<int:order_type_id>/items/", views.get_items_for_order_type, name="order-type-items"),
    path("orders/statistics/", views.get_order_statistics, name="order-statistics"),

    # Bunk-log date-scoped views
    path("bunklogs/all/<str:date>/", views.BunkLogsAllByDateViewSet.as_view(), name="all-bunk-logs-by-date"),
    path("bunklogs/<str:bunk_id>/logs/<str:date>/", views.BunkLogsInfoByDateViewSet.as_view(), name="bunklog-by-date"),

    # Camper logs history
    path("campers/<str:camper_id>/logs/", views.CamperBunkLogViewSet.as_view(), name="camper-bunklogs"),

    # Template-scoped aggregation dashboard and CSV export
    path(
        "dashboards/template/<int:template_id>/",
        template_dashboard.TemplateDashboardView.as_view(),
        name="template-dashboard",
    ),
    path(
        "dashboards/template/<int:template_id>/export/",
        template_dashboard.TemplateDashboardExportView.as_view(),
        name="template-dashboard-export",
    ),

    # Cross-roster coverage heatmap (commit 3 of 3.20)
    path(
        "dashboards/coverage/",
        coverage_dashboard.CoverageDashboardView.as_view(),
        name="dashboard-coverage",
    ),

    # Subject Trend Grid (commit 4 of 3.20)
    path(
        "dashboards/subject-trends/",
        trends_dashboard.SubjectTrendGridView.as_view(),
        name="dashboard-subject-trends",
    ),

    # Per-subject detail (commit 5 of 3.20)
    path(
        "dashboards/subject/<int:person_id>/",
        subject_dashboard.SubjectDetailView.as_view(),
        name="dashboard-subject-detail",
    ),

    # Unified per-group dashboard. Role + group-type-resolving
    # endpoint that replaces /api/v1/unit-head/bunks/<id>/ and
    # /api/v1/camper-care/bunks/<id>/ for bunks, and serves
    # unit/division/classroom rollups under the same surface.
    # Counselor, CC, UH, Leadership Team, and Admin read here for
    # camp groups; faculty/madrich read here for TBE classrooms. The
    # response includes a ``role_context`` block (role + group_type +
    # can_edit) driving frontend dispatch.
    path(
        "dashboards/group/<int:group_id>/",
        group_dashboard_api.GroupDashboardView.as_view(),
        name="dashboard-group",
    ),
    # Legacy bunk-only alias from the prior consolidation PR. Routes
    # to the same view (the view accepts either ``group_id`` or
    # ``bunk_id`` kwarg). Keep until external callers migrate.
    path(
        "dashboards/bunks/<int:bunk_id>/",
        group_dashboard_api.GroupDashboardView.as_view(),
        name="dashboard-bunk",
    ),

    # Author attribution (commit 6 of 3.20)
    path(
        "dashboards/authors/",
        authors_dashboard.AuthorAttributionView.as_view(),
        name="dashboard-authors",
    ),

    # Concerns Inbox (commit 7 of 3.20)
    path(
        "dashboards/concerns/",
        concerns_dashboard.ConcernsInboxView.as_view(),
        name="dashboard-concerns",
    ),
    path(
        "dashboards/concerns/<int:reflection_id>/<str:field_key>/read/",
        concerns_dashboard.ConcernMarkReadView.as_view(),
        name="dashboard-concerns-mark-read",
    ),

    # Unit head and camper care dashboard endpoints
    path("unithead/<str:unithead_id>/<str:date>/", views.get_unit_head_bunks, name="unit-head-bunks"),
    path("campercare/<str:camper_care_id>/<str:date>/", views.get_camper_care_bunks, name="camper-care-bunks"),

    # Counselor flow read endpoints (Step 7_6b)
    path(
        "counselor/dashboard/",
        counselor_dashboard.CounselorDashboardView.as_view(),
        name="counselor-dashboard",
    ),
    path(
        "counselor/camper-reflections/",
        counselor_camper_reflections.CamperReflectionListView.as_view(),
        name="counselor-camper-reflections",
    ),
    path(
        "counselor/self-reflection/history/",
        counselor_self_reflection.SelfReflectionHistoryView.as_view(),
        name="counselor-self-reflection-history",
    ),
    path(
        "counselor/requests/",
        counselor_requests.CounselorRequestsListView.as_view(),
        name="counselor-requests",
    ),

    # Counselor flow write endpoints (Step 7_6c)
    path(
        "counselor/camper-reflections/<int:reflection_id>/",
        counselor_camper_reflections.CamperReflectionDetailView.as_view(),
        name="counselor-camper-reflection-detail",
    ),
    path(
        "counselor/self-reflection/",
        counselor_self_reflection.SelfReflectionCreateView.as_view(),
        name="counselor-self-reflection-create",
    ),
    path(
        "counselor/self-reflection/<int:reflection_id>/",
        counselor_self_reflection.SelfReflectionDetailView.as_view(),
        name="counselor-self-reflection-detail",
    ),
    path(
        "counselor/camper-care-requests/",
        counselor_camper_care_requests.CamperCareRequestCreateView.as_view(),
        name="counselor-camper-care-create",
    ),
    path(
        "counselor/camper-care-item-suggestions/",
        counselor_camper_care_requests.CamperCareItemSuggestionListView.as_view(),
        name="counselor-camper-care-item-suggestions",
    ),
    path(
        "counselor/maintenance-tickets/",
        counselor_maintenance_tickets.MaintenanceTicketCreateView.as_view(),
        name="counselor-maintenance-ticket-create",
    ),
    path(
        "counselor/maintenance-tickets/<uuid:ticket_id>/photos/",
        counselor_maintenance_tickets.MaintenanceTicketPhotoCreateView.as_view(),
        name="counselor-maintenance-ticket-photo-create",
    ),
    # ------------------------------------------------------------------
    # Unit Head (Step 7_7)
    # Hyphenated namespace ``unit-head/`` deliberately disambiguates from
    # the legacy single-tenant ``unithead/`` route which still serves
    # Crane Lake's old User-based path.
    # ------------------------------------------------------------------
    path(
        "unit-head/dashboard/",
        uh_dashboard.UnitHeadDashboardView.as_view(),
        name="unit-head-dashboard",
    ),
    path(
        "unit-head/bunks/<int:bunk_id>/",
        uh_bunk_dashboard.UnitHeadBunkDashboardView.as_view(),
        name="unit-head-bunk-dashboard",
    ),
    path(
        "unit-head/campers/<int:camper_id>/",
        uh_camper_dashboard.UnitHeadCamperDashboardView.as_view(),
        name="unit-head-camper-dashboard",
    ),
    path(
        "unit-head/self-reflection/",
        uh_self_reflection.UnitHeadSelfReflectionCreateView.as_view(),
        name="unit-head-self-reflection-create",
    ),
    path(
        "unit-head/self-reflection/history/",
        uh_self_reflection.UnitHeadSelfReflectionHistoryView.as_view(),
        name="unit-head-self-reflection-history",
    ),
    path(
        "unit-head/self-reflection/<int:reflection_id>/",
        uh_self_reflection.UnitHeadSelfReflectionDetailView.as_view(),
        name="unit-head-self-reflection-detail",
    ),

    # ------------------------------------------------------------------
    # Camper Care (Step 7_8, Stories 18-23)
    # ------------------------------------------------------------------
    path(
        "camper-care/dashboard/",
        cc_dashboard.CamperCareDashboardView.as_view(),
        name="camper-care-dashboard",
    ),
    path(
        "camper-care/bunks/<int:bunk_id>/",
        cc_bunk_dashboard.CamperCareBunkDashboardView.as_view(),
        name="camper-care-bunk-dashboard",
    ),
    path(
        "camper-care/campers/<int:camper_id>/",
        cc_camper_dashboard.CamperCareCamperDashboardView.as_view(),
        name="camper-care-camper-dashboard",
    ),
    path(
        "camper-care/flags/",
        cc_flags.FlagListView.as_view(),
        name="camper-care-flags",
    ),
    path(
        "camper-care/flags/<uuid:flag_id>/",
        cc_flags.FlagDetailView.as_view(),
        name="camper-care-flag-detail",
    ),
    path(
        "camper-care/flags/<uuid:flag_id>/follow-up/",
        cc_flags.FlagFollowUpView.as_view(),
        name="camper-care-flag-follow-up",
    ),
    path(
        "camper-care/flags/<uuid:flag_id>/resolve/",
        cc_flags.FlagResolveView.as_view(),
        name="camper-care-flag-resolve",
    ),
    path(
        "camper-care/flags/<uuid:flag_id>/reopen/",
        cc_flags.FlagReopenView.as_view(),
        name="camper-care-flag-reopen",
    ),
    path(
        "camper-care/orders/",
        cc_orders.CamperCareOrdersListView.as_view(),
        name="camper-care-orders",
    ),
    path(
        "camper-care/orders/bulk-transition/",
        cc_orders.CamperCareOrderBulkTransitionView.as_view(),
        name="camper-care-orders-bulk-transition",
    ),
    path(
        "camper-care/orders/<uuid:order_id>/transition/",
        cc_orders.CamperCareOrderTransitionView.as_view(),
        name="camper-care-order-transition",
    ),
    path(
        "camper-care/self-reflection/",
        cc_self_reflection.CamperCareSelfReflectionCreateView.as_view(),
        name="camper-care-self-reflection",
    ),
    path(
        "camper-care/self-reflection/history/",
        cc_self_reflection.CamperCareSelfReflectionHistoryView.as_view(),
        name="camper-care-self-reflection-history",
    ),
    path(
        "camper-care/self-reflection/<int:reflection_id>/",
        cc_self_reflection.CamperCareSelfReflectionDetailView.as_view(),
        name="camper-care-self-reflection-detail",
    ),

    # ------------------------------------------------------------------
    # Specialist (Step 7_9, Stories 24-29)
    # ------------------------------------------------------------------
    path(
        "specialist/dashboard/",
        sp_dashboard.SpecialistDashboardView.as_view(),
        name="specialist-dashboard",
    ),
    path(
        "specialist/campers/",
        sp_campers.SpecialistCamperPickerView.as_view(),
        name="specialist-campers",
    ),
    path(
        "specialist/campers/<int:camper_id>/",
        sp_camper_view.SpecialistCamperView.as_view(),
        name="specialist-camper-view",
    ),
    path(
        "specialist/self-reflection/",
        sp_self_reflection.SpecialistSelfReflectionCreateView.as_view(),
        name="specialist-self-reflection-create",
    ),
    path(
        "specialist/self-reflection/history/",
        sp_self_reflection.SpecialistSelfReflectionHistoryView.as_view(),
        name="specialist-self-reflection-history",
    ),
    path(
        "specialist/self-reflection/<int:reflection_id>/",
        sp_self_reflection.SpecialistSelfReflectionDetailView.as_view(),
        name="specialist-self-reflection-detail",
    ),

    # ------------------------------------------------------------------
    # Leadership Team (Step 7_12, Stories 45-53)
    # ------------------------------------------------------------------
    path(
        "leadership-team/dashboard/",
        lt_dashboard.LeadershipTeamDashboardView.as_view(),
        name="leadership-team-dashboard",
    ),
    path(
        "leadership-team/teams/<str:team_role>/",
        lt_team_dashboard.LeadershipTeamTeamDashboardView.as_view(),
        name="leadership-team-team-dashboard",
    ),
    path(
        "leadership-team/teams/<str:team_role>/members/<int:membership_id>/reflection/",
        lt_member_reflection.LeadershipTeamMemberReflectionView.as_view(),
        name="leadership-team-member-reflection",
    ),
    path(
        "leadership-team/reflections/<int:reflection_id>/mark-attention/",
        lt_mark_attention.LeadershipTeamMarkAttentionView.as_view(),
        name="leadership-team-mark-attention",
    ),
    path(
        "leadership-team/self-reflection/",
        lt_self_reflection.LeadershipTeamSelfReflectionCreateView.as_view(),
        name="leadership-team-self-reflection-create",
    ),
    path(
        "leadership-team/self-reflection/<int:reflection_id>/",
        lt_self_reflection.LeadershipTeamSelfReflectionDetailView.as_view(),
        name="leadership-team-self-reflection-detail",
    ),
    # LT template builder (Step 7_12 PR B — Story 51)
    path(
        "leadership-team/templates/",
        lt_templates.LeadershipTeamTemplateListCreateView.as_view(),
        name="leadership-team-templates",
    ),
    path(
        "leadership-team/templates/<int:pk>/",
        lt_templates.LeadershipTeamTemplateDetailView.as_view(),
        name="leadership-team-template-detail",
    ),
    path(
        "leadership-team/templates/<int:pk>/publish/",
        lt_templates.LeadershipTeamTemplatePublishView.as_view(),
        name="leadership-team-template-publish",
    ),
    path(
        "leadership-team/templates/<int:pk>/unpublish/",
        lt_templates.LeadershipTeamTemplateUnpublishView.as_view(),
        name="leadership-team-template-unpublish",
    ),
    path(
        "leadership-team/templates/<int:pk>/archive/",
        lt_templates.LeadershipTeamTemplateArchiveView.as_view(),
        name="leadership-team-template-archive",
    ),
    path(
        "leadership-team/templates/<int:pk>/clone/",
        lt_templates.LeadershipTeamTemplateCloneView.as_view(),
        name="leadership-team-template-clone",
    ),
    # LT assignments (Step 7_12 PR B — Story 52)
    path(
        "leadership-team/assignments/",
        lt_assignments.LeadershipTeamAssignmentListCreateView.as_view(),
        name="leadership-team-assignments",
    ),
    path(
        "leadership-team/assignments/<int:pk>/",
        lt_assignments.LeadershipTeamAssignmentDetailView.as_view(),
        name="leadership-team-assignment-detail",
    ),
    # LT responses + exports (Story 53, Story 48 c5/c6)
    path(
        "leadership-team/templates/<int:template_id>/responses/",
        lt_responses.LeadershipTeamTemplateResponsesView.as_view(),
        name="leadership-team-template-responses",
    ),
    path(
        "leadership-team/templates/<int:template_id>/responses/export/",
        lt_exports.LeadershipTeamTemplateResponsesExportView.as_view(),
        name="leadership-team-template-responses-export",
    ),
    path(
        "leadership-team/teams/<str:team_role>/aggregate/export/",
        lt_exports.LeadershipTeamTeamAggregateExportView.as_view(),
        name="leadership-team-team-aggregate-export",
    ),

    # ------------------------------------------------------------------
    # Observations (Step 7_23) — the converged note system. Specific paths
    # are listed before ``observations/<id>/`` so they route correctly.
    # ------------------------------------------------------------------
    path(
        "observations/inbox/",
        observations_views.ObservationsInboxView.as_view(),
        name="observations-inbox",
    ),
    path(
        "observations/sent/",
        observations_views.ObservationsSentView.as_view(),
        name="observations-sent",
    ),
    path(
        "observations/unread-count/",
        observations_views.ObservationsUnreadCountView.as_view(),
        name="observations-unread-count",
    ),
    path(
        "observations/recipient-candidates/",
        observations_views.ObservationRecipientCandidatesView.as_view(),
        name="observations-recipient-candidates",
    ),
    path(
        "observations/subjects/",
        observations_views.ObservationSubjectsView.as_view(),
        name="observations-subjects",
    ),
    path(
        "observations/",
        observations_views.ObservationCreateView.as_view(),
        name="observations-create",
    ),
    path(
        "observations/<int:observation_id>/",
        observations_views.ObservationThreadView.as_view(),
        name="observations-thread",
    ),
    path(
        "observations/<int:observation_id>/replies/",
        observations_views.ObservationReplyCreateView.as_view(),
        name="observations-reply-create",
    ),
    path(
        "observations/<int:observation_id>/amend/",
        observations_views.ObservationAmendView.as_view(),
        name="observations-amend",
    ),
    path(
        "observations/<int:observation_id>/archive/",
        observations_views.ObservationArchiveView.as_view(),
        name="observations-archive-action",
    ),
    path(
        "observations/<int:observation_id>/unarchive/",
        observations_views.ObservationUnarchiveView.as_view(),
        name="observations-unarchive-action",
    ),
]

app_name = "api"
