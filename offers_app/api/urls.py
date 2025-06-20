from django.urls import path, include
from .views import (
    OffersViewSet
)
from rest_framework.routers import DefaultRouter
router = DefaultRouter()
router.register(r'offers', OffersViewSet, basename='offers')

urlpatterns = [
     path('', include(router.urls)),
]
