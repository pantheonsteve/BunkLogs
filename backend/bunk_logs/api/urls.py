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
from .camper_care import notes as cc_notes
from .camper_care import orders as cc_orders
from .counselor import camper_care_requests as counselor_camper_care_requests
from .counselor import camper_reflections as counselor_camper_reflections
from .counselor import dashboard as counselor_dashboard
from .counselor import maintenance_tickets as counselor_maintenance_tickets
from .counselor import requests as counselor_requests
from .counselor import self_reflection as counselor_self_reflection
from .dashboards import authors as authors_dashboard
from .dashboards import concerns as concerns_dashboard
from .dashboards import coverage as coverage_dashboard
from .dashboards import subject as subject_dashboard
from .dashboards import template as template_dashboard
from .dashboards import trends as trends_dashboard
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
    path("", include(router.urls)),

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
        "camper-care/notes/",
        cc_notes.CamperCareNoteCreateView.as_view(),
        name="camper-care-note-create",
    ),
    path(
        "camper-care/notes/audience/",
        cc_notes.CamperCareNoteAudienceView.as_view(),
        name="camper-care-note-audience",
    ),
    path(
        "camper-care/notes/<int:note_id>/",
        cc_notes.CamperCareNoteDetailView.as_view(),
        name="camper-care-note-detail",
    ),
]

app_name = "api"
