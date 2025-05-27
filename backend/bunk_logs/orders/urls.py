from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = "orders"

router = DefaultRouter()
router.register(r'', views.OrderViewSet, basename='order')
router.register(r'items', views.ItemViewSet, basename='item')
router.register(r'order-types', views.OrderTypeViewSet, basename='order-type')
router.register(r'item-categories', views.ItemCategoryViewSet, basename='item-category')

urlpatterns = [
    path('', include(router.urls)),
    path('get_items_by_order_type/', views.get_items_by_order_type, name='get_items_by_order_type'),
]
