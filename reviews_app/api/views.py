from django.contrib.auth.models import User
from rest_framework import viewsets, status
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from ..models import Review
from .serializers import ReviewReadSerializer, ReviewCreateSerializer
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

    # Configuration for filtering and ordering.
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

        This is a key pattern for separating read and write concerns. Write actions use a
        serializer with validation for input, while read actions use a different
        serializer optimized for output representation.
        """
        if self.action == 'create':
            # Use the specialized serializer for creating new reviews.
            return ReviewCreateSerializer

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
        Overrides the default `create` behavior to add custom logic.

        This implementation performs two key tasks:
        1.  It checks for duplicate reviews before attempting to save, returning a
            more specific `403 Forbidden` status if one exists.
        2.  It uses the `ReviewReadSerializer` to format the success response, ensuring
            the returned object is complete and consistent with a GET request.
        """
        business_user_id = request.data.get('business_user')
        # Check if this reviewer has already reviewed this business user.
        if business_user_id and Review.objects.filter(
            business_user_id=business_user_id,
            reviewer=request.user
        ).exists():
            return Response(
                {"detail": "You have already submitted a review for this business."},
                status=status.HTTP_403_FORBIDDEN
            )

        # 1. Use the write serializer (`ReviewCreateSerializer`) to validate input.
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)  # This saves the object

        # 2. Use the read serializer (`ReviewReadSerializer`) to create the response data.
        instance = serializer.instance
        read_serializer = ReviewReadSerializer(instance, context={'request': request})

        headers = self.get_success_headers(read_serializer.data)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
