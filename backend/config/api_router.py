from django.conf import settings
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from bunk_logs.users.api.views import UserViewSet
from bunk_logs.api.views import (
    # Ordering system views
    OrderViewSet, ItemViewSet, ItemCategoryViewSet, OrderTypeViewSet,
    get_items_for_order_type, get_order_statistics,
    # Core bunk logs views
    UnitViewSet, UnitStaffAssignmentViewSet, BunkViewSet,
    CamperViewSet, CamperBunkAssignmentViewSet, BunkLogViewSet, CounselorLogViewSet,
    # API views for specific endpoints
    BunkLogsInfoByDateViewSet, BunkLogsAllByDateViewSet, CamperBunkLogViewSet,
    get_user_by_email, debug_user_bunks, FixSocialAppsView,
    get_unit_head_bunks, get_camper_care_bunks, UserDetailsView
)

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

# User management
router.register("users", UserViewSet, basename='user')

# Core bunk logs functionality
router.register("units", UnitViewSet, basename='unit')
router.register("unit-staff-assignments", UnitStaffAssignmentViewSet, basename='unit-staff-assignment')
router.register("bunks", BunkViewSet, basename='bunk')
router.register("campers", CamperViewSet, basename='camper')
router.register("camper-bunk-assignments", CamperBunkAssignmentViewSet, basename='camper-bunk-assignment')
router.register("bunk-logs", BunkLogViewSet, basename='bunk-log')
router.register("counselor-logs", CounselorLogViewSet, basename='counselor-log')

# Ordering system
router.register("orders", OrderViewSet, basename='order')
router.register("items", ItemViewSet, basename='item')
router.register("item-categories", ItemCategoryViewSet, basename='item-category')
router.register("order-types", OrderTypeViewSet, basename='order-type')

# Custom URL patterns for additional endpoints
custom_urlpatterns = [
    # Ordering system endpoints
    path('order-types/<int:order_type_id>/items/', get_items_for_order_type, name='order-type-items'),
    path('orders/statistics/', get_order_statistics, name='order-statistics'),
    
    # Bunk logs specific endpoints
    path('bunklogs/<str:bunk_id>/logs/<str:date>/', BunkLogsInfoByDateViewSet.as_view(), name='bunk-logs-by-date'),
    path('bunklogs/all/<str:date>/', BunkLogsAllByDateViewSet.as_view(), name='all-bunk-logs-by-date'),
    path('campers/<str:camper_id>/logs/', CamperBunkLogViewSet.as_view(), name='camper-bunk-logs'),
    
    # User and staff management endpoints
    path('users/email/<str:email>/', get_user_by_email, name='user-by-email'),
    path('users/details/', UserDetailsView.as_view({'get': 'list'}), name='user-details'),
    path('debug/user-bunks/', debug_user_bunks, name='debug-user-bunks'),
    path('debug/fix-social-apps/', FixSocialAppsView.as_view(), name='fix-social-apps'),
    
    # Unit and staff specific endpoints
    path('unithead/<str:unithead_id>/<str:date>/', get_unit_head_bunks, name='unit-head-bunks'),
    path('campercare/<str:camper_care_id>/<str:date>/', get_camper_care_bunks, name='camper-care-bunks'),
]

app_name = "api"
urlpatterns = router.urls + custom_urlpatterns
