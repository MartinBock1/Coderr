from rest_framework import viewsets
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Min
from django_filters.rest_framework import DjangoFilterBackend

from offers_app.models import Offer, OfferDetail
from .serializers import (
    OfferListSerializer, 
    OfferDetailUrlSerializer,
)
from .filters import OfferFilter

class OfferViewSet(viewsets.ModelViewSet):
    serializer_class = OfferListSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = OfferFilter
    search_fields = ['title', 'description']
    ordering_fields = ['updated_at', 'min_price']
    
    def get_queryset(self):
        """
        Annotate the queryset with calculated values for min_price and min_delivery_time.
        """
        return Offer.objects.annotate(
            min_price=Min('details__price'),
            min_delivery_time_days=Min('details__delivery_time_days')
        ).select_related('user').prefetch_related('details').order_by('-updated_at')

# Wir brauchen einen minimalen ViewSet für OfferDetail, damit die Hyperlinks funktionieren
class OfferDetailViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = OfferDetail.objects.all()
    serializer_class = OfferDetailUrlSerializer # Verwenden Sie einen passenden Serializer