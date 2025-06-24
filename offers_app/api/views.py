from rest_framework import viewsets, status
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated, AllowAny 
from rest_framework.response import Response
from django.db.models import Min
from django_filters.rest_framework import DjangoFilterBackend

from offers_app.models import Offer, OfferDetail
from .serializers import (
    OfferListSerializer,
    OfferCreateUpdateSerializer,
    OfferDetailUrlSerializer,
    OfferResponseSerializer,
)
from .filters import OfferFilter
from .permissions import IsBusinessUser
from .pagination import StandardResultsSetPagination


class OfferViewSet(viewsets.ModelViewSet):
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = OfferFilter
    search_fields = ['title', 'description']
    ordering_fields = ['updated_at', 'min_price']
    
    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            # Authentication is required for write actions
            self.permission_classes = [IsBusinessUser ]
        else:
            # No authentication is required for read actions (list, retrieve)
            self.permission_classes = [AllowAny]
        return super().get_permissions()

    def get_queryset(self):
        """
        Annotate the queryset with calculated values for min_price and min_delivery_time.
        """
        return Offer.objects.annotate(
            min_price=Min('details__price'),
            min_delivery_time_days=Min('details__delivery_time_days')
        ).select_related('user').prefetch_related('details').order_by('-updated_at')
    
    def get_serializer_class(self):
        """
        Return the appropriate serializer class based on the request action.
        """
        if self.action in ['create', 'update', 'partial_update']:
            return OfferCreateUpdateSerializer # create/post/update/patch
        return OfferListSerializer  # list/retrieve
    
    def perform_create(self, serializer):
        """
        Automatically assign the logged-in user to the offer upon creation.
        """
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        instance = serializer.instance
        read_serializer = OfferResponseSerializer(instance, context=self.get_serializer_context())
        headers = self.get_success_headers(read_serializer.data)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
# Wir brauchen einen minimalen ViewSet für OfferDetail, damit die Hyperlinks funktionieren
class OfferDetailViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = OfferDetail.objects.all()
    serializer_class = OfferDetailUrlSerializer  # Verwenden Sie einen passenden Serializer
