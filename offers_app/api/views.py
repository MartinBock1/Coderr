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
        Dynamically assigns permission classes for the ViewSet based on the request's action.

        This method is a core part of DRF's policy implementation. Since a ViewSet
        bundles multiple endpoints (list, create, retrieve, update, destroy) into a
        single class, this hook allows for applying different security rules to each
        specific action. It inspects `self.action` (a string like 'list' or 'create')
        to determine the appropriate permissions for the incoming request.

        The implemented access control logic is as follows:
        -   **Write actions on existing objects (`update`, `destroy`):**
            Requires object-level permission. Only the user who owns the offer can
            modify or delete it. This is handled by `IsOwnerOrReadOnly`.
        -   **Creation (`create`):**
            Requires role-based permission. Only users with a 'business' profile
            are allowed to create new offers, enforced by `IsBusinessUser`.
        -   **Retrieval of a single item (`retrieve`):**
            Requires basic authentication. Any logged-in user can view the details
            of any offer.
        -   **Listing all items (`list`):**
            Publicly accessible. Anyone, including anonymous users, can browse the
            list of offers.

        Returns:
            list: A list of instantiated permission objects that DRF will
                  sequentially check to authorize the request.
        """
        # For actions that modify or delete a specific, existing object.
        # The `IsOwnerOrReadOnly` permission checks for both authentication and
        # that `request.user` matches the `obj.user` field.
        if self.action in ['update', 'partial_update', 'destroy']:
            # This sets the permission classes to be used for this specific request.
            self.permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

        # For the action of creating a new object. This is a view-level permission,
        # as there is no object to check ownership against yet.
        elif self.action == 'create':
            # `IsBusinessUser` checks if `request.user.profile.type` is 'business'.
            self.permission_classes = [IsBusinessUser]

        # For the action of retrieving a single object's details.
        elif self.action == 'retrieve':
            # `IsAuthenticated` simply ensures the request comes from a logged-in user.
            self.permission_classes = [IsAuthenticated]
            
        # This `else` block serves as the default for any other actions,
        # which in a standard ModelViewSet is primarily the 'list' action.
        else:
            # `AllowAny` grants unrestricted access, making the list of offers public.
            self.permission_classes = [AllowAny]

        # Crucially, call the parent method. This takes the list of permission *classes*
        # we've just set on `self.permission_classes` and returns a list of *instances*
        # of those classes, which DRF can then execute to check permissions.
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
        Handles the HTTP DELETE request to delete a specific Offer.

        This method orchestrates the deletion of an object by leveraging DRF's
        built-in generic view functionality. The core logic for authorization
        (i.e., checking for authentication and ownership via IsOwnerOrReadOnly)
        is handled by DRF's permission system *before* this method is executed,
        as configured in `get_permissions()`.

        The process within this method is:
        1.  Retrieve the target object using `get_object()`.
        2.  Delete the object from the database via `perform_destroy()`.
        3.  Return a standard success response.

        Args:
            request: The incoming HttpRequest object.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments, which will contain the
                      primary key ('pk') from the URL.

        Returns:
            Response: An empty DRF Response object with an HTTP 204 No Content
                      status on successful deletion.
                      DRF automatically handles returning:
                      - 401 Unauthorized if the user is not authenticated.
                      - 403 Forbidden if the user is not the owner.
                      - 404 Not Found if the object does not exist.
        """
        # Step 1: Retrieve the specific offer instance to be deleted.
        # This DRF helper method uses the primary key from the URL (`kwargs['pk']`).
        # It automatically handles two critical tasks:
        #   1. Raises an `Http404` if no object with the given pk is found,
        #      resulting in a 404 Not Found response.
        #   2. Triggers the object-level permission checks (e.g., IsOwnerOrReadOnly)
        #      that were configured for this action in `get_permissions()`.
        instance = self.get_object()
        
        # Step 2: Call the DRF helper to delete the object from the database.
        # This method, by default, simply calls `instance.delete()`. Using this
        # hook is a best practice, as it allows for custom pre- or post-delete
        # logic to be added later by overriding it.
        self.perform_destroy(instance)
        
        # Step 3: Return a success response.
        # HTTP 204 No Content is the standard and expected response for a
        # successful DELETE operation. It indicates success but signals to the
        # client that there is no response body to parse.
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
