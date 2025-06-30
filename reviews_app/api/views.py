from django.contrib.auth.models import User
from rest_framework import viewsets, status
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from ..models import Review
from .serializers import (
    ReviewReadSerializer,
    ReviewCreateSerializer,
    ReviewUpdateSerializer
)
from .filters import ReviewFilter
from .permissions import IsCustomerUser, IsOwnerOrReadOnly


class ReviewViewSet(viewsets.ModelViewSet):
    """
    Manages all CRUD (Create, Retrieve, Update, Delete) operations for reviews.

    This ViewSet provides the following endpoints:
    - `GET /api/reviews/`: Lists all reviews with filtering and ordering.
    - `POST /api/reviews/`: Creates a new review.
    - `GET /api/reviews/{id}/`: Retrieves a single review.
    - `PUT/PATCH /api/reviews/{id}/`: Updates a review.
    - `DELETE /api/reviews/{id}/`: Deletes a review.

    Key features include dynamic permission handling, separate serializers for read
    and write operations, and custom logic to prevent duplicate reviews.
    """
    # The base queryset for all requests.
    # `.select_related('reviewer', 'business_user')` is a performance optimization that
    # pre-fetches the related User objects in a single database query, preventing
    # the N+1 query problem.
    queryset = Review.objects.all().select_related('reviewer', 'business_user')
    
    # Default serializer class, used for read actions unless overridden by `get_serializer_class`.
    serializer_class = ReviewReadSerializer

    # Pagination is disabled for this view; all results will be returned in a single response.
    pagination_class = None

    # Configuration for enabling filtering (by user) and ordering (by date, rating).
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = ReviewFilter
    ordering_fields = ['updated_at', 'rating']

    def get_permissions(self):
        """
        Dynamically assigns permissions based on the current action.

        This ensures that endpoint access is appropriately restricted:
        - 'create': Only users with a 'customer' profile can create reviews.
        - 'update', 'destroy': Only the original author of the review can modify or delete it.
        - 'list', 'retrieve': Any authenticated user can view reviews.
        """
        if self.action == 'create':
            # For creating a new review, the user must be a customer.
            permission_classes = [IsCustomerUser]
        elif self.action in ['update', 'partial_update', 'destroy']:
            # For modifying an existing review, the user must be the owner.
            permission_classes = [IsOwnerOrReadOnly]
        else:
            # For all other actions (list, retrieve), the user just needs to be authenticated.
            permission_classes = [IsAuthenticated]
        # Instantiate and return the permission classes.
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        """
        Returns the appropriate serializer class based on the request action.

        This allows for different validation rules and fields for creating, updating,
        and reading data, a core best practice for robust APIs.
        """
        if self.action == 'create':
            # Use the specialized serializer for creating new reviews.
            return ReviewCreateSerializer

        if self.action in ['update', 'partial_update']:
            return ReviewUpdateSerializer

        # For all other actions (list, retrieve, update), use the read-optimized serializer.
        return ReviewReadSerializer

    def perform_create(self, serializer):
        """
        A hook called by `create()` to automatically assign the logged-in user as the reviewer.

        This ensures the 'reviewer' field is set securely on the server side and is not
        dependent on the client's payload.
        """
        serializer.save(reviewer=self.request.user)

    def create(self, request, *args, **kwargs):
        """
        Overrides the default `create` behavior. The validation logic, including
        the check for duplicate reviews, is now fully handled by the serializer.
        """
        
        # 1. Use the write serializer (`ReviewCreateSerializer`) to validate input.
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)  # This saves the object

        # 2. Use the read serializer (`ReviewReadSerializer`) to create the response data.
        instance = serializer.instance
        read_serializer = ReviewReadSerializer(instance, context={'request': request})

        headers = self.get_success_headers(read_serializer.data)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        """
        Overrides the default update behavior to return the full, updated object.
        
        This ensures that the API response after a PATCH/PUT is consistent and contains the
        complete representation of the resource.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # Use the write serializer (ReviewUpdateSerializer) for validation and saving
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been used, the cache may be stale
            # after the update. Clear it to ensure the response serializer
            # gets the fresh, updated data from related models if any existed.
            instance._prefetched_objects_cache = {}

        # Use the read serializer (ReviewReadSerializer) for the response
        read_serializer = ReviewReadSerializer(instance, context={'request': request})
        return Response(read_serializer.data)
