from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'users', views.UserDetailsView, basename='user')
# Add other viewsets to the router
router.register(r'bunks', views.BunkViewSet, basename='bunk')
router.register(r'units', views.UnitViewSet, basename='unit')
router.register(r'unit-staff-assignments', views.UnitStaffAssignmentViewSet, basename='unit-staff-assignment')
router.register(r'campers', views.CamperViewSet, basename='camper')
router.register(r'camper-bunk-assignments', views.CamperBunkAssignmentViewSet, basename='camper-bunk-assignment')
router.register(r'bunklogs', views.BunkLogViewSet, basename='bunklog')
router.register(r'counselorlogs', views.CounselorLogViewSet, basename='counselorlog')
# router.register(r'orders', views.OrderViewSet, basename='order')
# router.register(r'items', views.ItemViewSet, basename='item')

urlpatterns = [
    path('', include(router.urls)),
    # Add a URL pattern for an individual bunk
    path('bunk/<str:id>/', views.BunkViewSet.as_view({'get': 'retrieve'}), name='bunk-detail'),
    
    # User registration endpoint
    path('users/create/', views.UserCreate.as_view(), name='user-create'),
    
    # Add dedicated endpoint for email-based user retrieval
    path('users/email/<str:email>/', views.get_user_by_email, name='user-by-email'),
     # Add a URL pattern for the BunkLogsInfoByDateViewSet
    path('users/<str:user_id>', views.get_user_by_id, name='user-by-id'),
    path('bunklogs/<str:bunk_id>/logs/<str:date>/', views.BunkLogsInfoByDateViewSet.as_view(), name='bunklog-by-date'),
    # URL for camper bunk logs
    path('campers/<str:camper_id>/logs/', views.CamperBunkLogViewSet.as_view(), name='camper-bunklogs'),
    
    # Unit Head and Camper Care endpoints
    path('unithead/<str:unithead_id>/<str:date>/', views.get_unit_head_bunks, name='unit-head-bunks'),
    path('campercare/<str:camper_care_id>/<str:date>/', views.get_camper_care_bunks, name='camper-care-bunks'),
    
    # Debug endpoints
    path('debug/user-bunks/', views.debug_user_bunks, name='debug-user-bunks'),
    path('debug/fix-social-apps/', views.FixSocialAppsView.as_view(), name='fix-social-apps'),
    path('debug/auth/', views.auth_debug_view, name='auth-debug'),
]


