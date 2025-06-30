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
    OfferDetailReadSerializer,
    OfferResponseSerializer,
    OfferRetrieveSerializer,
)
from .filters import OfferFilter
from .permissions import IsBusinessUser, IsOwnerOrReadOnly
from .pagination import StandardResultsSetPagination


class OfferViewSet(viewsets.ModelViewSet):
    """
    Manages all CRUD operations for the Offer model.

    This ViewSet provides the following endpoints:
    - `GET /api/offers/`: Lists all offers with pagination, filtering, and searching.
    - `POST /api/offers/`: Creates a new offer with its nested detail packages.
    - `GET /api/offers/{id}/`: Retrieves a single, detailed offer.
    - `PATCH /api/offers/{id}/`: Partially updates an offer and its nested details.
    - `DELETE /api/offers/{id}/`: Deletes an offer.

    Key Features:
    - Dynamic permission handling based on the action (e.g., create, update).
    - Highly optimized database queries using queryset annotations and prefetching.
    - Dynamic serializer selection to separate read, write, and list representations.
    - Custom logic for creating and updating nested OfferDetail objects.
    """
    # --- ViewSet Configuration ---
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = OfferFilter
    search_fields = ['title', 'description']
    ordering_fields = ['updated_at', 'min_price']
    
    def get_permissions(self):
        """
        Dynamically sets permissions based on the current action.

        This ensures that endpoint access is appropriately restricted:
        - `update`, `partial_update`, `destroy`: Only the owner can modify/delete.
        - `create`: Only users with a 'business' profile can create offers.
        - `retrieve`: Any authenticated user can view a single offer's details.
        - `list`: Anyone (authenticated or not) can browse the list of offers.
        """
        if self.action in ['update', 'partial_update']:
            # For write operations on an existing object, only the owner has permission.
            self.permission_classes = [IsOwnerOrReadOnly]
        elif self.action == 'create':
            # Only users with a 'business' profile are allowed to create new offers.
            self.permission_classes = [IsBusinessUser]
        elif self.action == 'retrieve':
            # Any logged-in user can view the details of a single offer.
            self.permission_classes = [IsAuthenticated]
        # elif self.action == 'destroy':
            # self.permission_classes = [AllowAny]
        else:
            # The list view is public and accessible to anyone.
            self.permission_classes = [AllowAny]
        return super().get_permissions()

    def get_queryset(self):
        """
        Builds the base queryset for all list and detail views.

        This method is optimized for performance by:
        1.  `annotate()`: Calculating `min_price` and `min_delivery_time_days`
            in the database to avoid extra calculations in Python.
        2.  `select_related('user')`: Fetching the related User object with a
            single SQL JOIN, preventing the N+1 query problem for user data.
        3.  `prefetch_related('details')`: Fetching all related OfferDetail objects
            in a separate, efficient query, preventing the N+1 problem for details.
        """
        return Offer.objects.annotate(
            min_price=Min('details__price'),
            min_delivery_time_days=Min('details__delivery_time_in_days')
        ).select_related('user').prefetch_related('details').order_by('-updated_at')
    
    def get_serializer_class(self):
        """
        Returns the appropriate serializer class based on the request action.

        This is a key pattern for separating read and write concerns:
        - Write actions (`create`, `update`) use a serializer for input validation and saving.
        - Read actions (`list`, `retrieve`) use different serializers optimized for output.
        """
        if self.action in ['create', 'update', 'partial_update']:
            return OfferCreateUpdateSerializer
        if self.action == 'retrieve':
            # This serializer is specifically designed for the retrieve action
            # and matches the API specification exactly.
            return OfferRetrieveSerializer
        # For the list view, use the more lightweight list serializer.
        return OfferListSerializer
    
    def perform_create(self, serializer):
        """
        A hook called by `create()` to automatically assign the logged-in user as the owner of the
        new offer.
        """
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        """
        Overrides the default `create` behavior to return a detailed response.

        The standard `create` would return data structured by the write serializer. This custom
        implementation saves the object and then uses the dedicated `OfferResponseSerializer` to
        return the complete object, including all server-generated fields and nested details.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        instance = serializer.instance
        # Serialize the new instance using the response serializer for a rich output.
        read_serializer = OfferResponseSerializer(instance, context=self.get_serializer_context())
        headers = self.get_success_headers(read_serializer.data)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        """
        Overrides the default `update` behavior for both PUT and PATCH requests.

        Similar to `create`, this ensures that after a successful update, the response body
        contains the full, updated object representation using the `OfferResponseSerializer`.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' was used, the cache is now stale.
            # Reload the instance from the DB to get the updated nested details.
            instance = self.get_object()
        
        # Serialize the updated instance for the response.
        read_serializer = OfferResponseSerializer(instance, context=self.get_serializer_context())
        return Response(read_serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        Custom destroy method to enforce a specific order of checks as per the API documentation:
        1. Check if the object exists (404).
        2. Check if the user is authenticated (401).
        3. Check if the user is the owner (403).
        """
        # 1. PRÜFUNG: Existiert das Objekt?
        # Wir holen das Objekt direkt. Wenn es nicht existiert, wird hier ein 404 ausgelöst,
        # bevor irgendeine Berechtigungsprüfung stattfindet.
        instance = self.get_object()

        # 2. PRÜFUNG: Ist der Benutzer authentifiziert?
        # Wir führen die IsAuthenticated-Prüfung manuell durch.
        if not request.user or not request.user.is_authenticated:
            # Wenn nicht, geben wir den geforderten 401-Fehler zurück.
            # self.permission_denied löst normalerweise einen 403 aus, daher erstellen wir die Response manuell.
            return Response(
                {"detail": "Authentication credentials were not provided."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # 3. PRÜFUNG: Ist der authentifizierte Benutzer der Besitzer?
        # Wir instanziieren die IsOwnerOrReadOnly-Klasse und rufen ihre Prüfmethode auf.
        permission = IsOwnerOrReadOnly()
        if not permission.has_object_permission(request, self, instance):
            # Wenn nicht, löst diese Methode einen 403 Forbidden aus.
            self.permission_denied(
                request, message=getattr(permission, 'message', None)
            )

        # 4. AKTION: Wenn alle Prüfungen erfolgreich waren, löschen wir das Objekt.
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class OfferDetailViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Provides read-only access to OfferDetail objects.

    This ViewSet is primarily used to power the hyperlinked URLs provided
    in the `OfferListSerializer`. It exposes the following endpoints:
    - `GET /api/offerdetails/`
    - `GET /api/offerdetails/{id}/`
    """
    queryset = OfferDetail.objects.all()
    serializer_class = OfferDetailReadSerializer
    permission_classes = [IsAuthenticated]
