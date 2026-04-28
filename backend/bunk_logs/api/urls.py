from django.urls import include
from django.urls import path
from rest_framework.routers import DefaultRouter

from bunk_logs.users.api.views import UserViewSet

from . import views

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

# Ordering system
router.register(r"orders", views.OrderViewSet, basename="order")
router.register(r"items", views.ItemViewSet, basename="item")
router.register(r"item-categories", views.ItemCategoryViewSet, basename="item-category")
router.register(r"order-types", views.OrderTypeViewSet, basename="order-type")

urlpatterns = [
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

    # Unit head and camper care dashboard endpoints
    path("unithead/<str:unithead_id>/<str:date>/", views.get_unit_head_bunks, name="unit-head-bunks"),
    path("campercare/<str:camper_care_id>/<str:date>/", views.get_camper_care_bunks, name="camper-care-bunks"),
]

app_name = "api"
