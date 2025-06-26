from django.urls import path, include
from .views import (
    OrderViewSet,
    OrderCountView,
    CompletedOrderCountView,
)
from rest_framework.routers import DefaultRouter
router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')

urlpatterns = router.urls

urlpatterns = [
     path('', include(router.urls)),
     path('order-count/<int:business_user_id>/', OrderCountView.as_view(), name='order-count'),
     path('completed-order-count/<int:business_user_id>/', CompletedOrderCountView.as_view(), name='completed-order-count'),
]