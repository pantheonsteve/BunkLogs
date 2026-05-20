from django.urls import include
from django.urls import path
from rest_framework.routers import DefaultRouter

from bunk_logs.users.api.views import UserViewSet

from . import assignment_groups
from . import audit as audit_api
from . import field_keys as field_keys_api
from . import memberships
from . import orders_state_machine as order_sm
from . import reflections
from . import supervisions as supervisions_api
from . import templates as templates_api
from . import views
from .dashboards import authors as authors_dashboard
from .dashboards import concerns as concerns_dashboard
from .dashboards import coverage as coverage_dashboard
from .dashboards import subject as subject_dashboard
from .dashboards import template as template_dashboard
from .dashboards import trends as trends_dashboard

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
]

app_name = "api"
