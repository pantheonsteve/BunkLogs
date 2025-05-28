from django.conf import settings
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from bunk_logs.users.api.views import UserViewSet
from bunk_logs.api.views import (
    OrderViewSet, ItemViewSet, ItemCategoryViewSet, OrderTypeViewSet,
    get_items_for_order_type, get_order_statistics
)

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("users", UserViewSet, basename='user')
router.register("orders", OrderViewSet, basename='order')
router.register("items", ItemViewSet, basename='item')
router.register("item-categories", ItemCategoryViewSet, basename='item-category')
router.register("order-types", OrderTypeViewSet, basename='order-type')

# Custom URL patterns for additional endpoints
custom_urlpatterns = [
    path('order-types/<int:order_type_id>/items/', get_items_for_order_type, name='order-type-items'),
    path('orders/statistics/', get_order_statistics, name='order-statistics'),
]

app_name = "api"
urlpatterns = router.urls + custom_urlpatterns
