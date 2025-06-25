from django.urls import path, include
from .views import (
    OrderViewSet,
    # OfferDetailViewSet
)
from rest_framework.routers import DefaultRouter
router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')
# router.register(r'offerdetails', OfferDetailViewSet, basename='offerdetail')

urlpatterns = router.urls

urlpatterns = [
     path('', include(router.urls)),
]