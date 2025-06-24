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
    OfferRetrieveSerializer,
)
from .filters import OfferFilter
from .permissions import IsBusinessUser, IsOwnerOrReadOnly
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
        if self.action in ['update', 'partial_update', 'destroy']:
            # Nur der Eigentümer des Objekts darf es bearbeiten.
            self.permission_classes = [IsOwnerOrReadOnly]
        elif self.action == 'create':
            self.permission_classes = [IsBusinessUser]
        elif self.action == 'retrieve':
            self.permission_classes = [IsAuthenticated]
        else:
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
            return OfferCreateUpdateSerializer
        if self.action == 'retrieve':
            return OfferRetrieveSerializer
        return OfferListSerializer
    
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
        # Use the dedicated response serializer to return the full object
        read_serializer = OfferResponseSerializer(instance, context=self.get_serializer_context())
        headers = self.get_success_headers(read_serializer.data)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    # +++ START: NEUE/GEÄNDERTE METHODEN FÜR UPDATE +++

    def perform_update(self, serializer):
        """
        Handles the actual saving of the instance during an update.
        Called by update() and partial_update().
        """
        serializer.save()

    def update(self, request, *args, **kwargs):
        """
        Handles PUT and PATCH requests.
        After a successful update, it returns the complete, updated object
        using the dedicated response serializer.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been used, we need to reload the instance
            # from the database to get the updated data.
            instance = self.get_object()
        
        # Use the dedicated response serializer to return the full object
        read_serializer = OfferResponseSerializer(instance, context=self.get_serializer_context())
        return Response(read_serializer.data)

    def partial_update(self, request, *args, **kwargs):
        """
        Ensures PATCH requests are handled by the update method with partial=True.
        """
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
# Wir brauchen einen minimalen ViewSet für OfferDetail, damit die Hyperlinks funktionieren
class OfferDetailViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = OfferDetail.objects.all()
    serializer_class = OfferDetailUrlSerializer  # Verwenden Sie einen passenden Serializer
