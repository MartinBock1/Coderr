from rest_framework import generics, permissions

from profile_app.models import Profile
from .permissions import IsOwnerOrReadOnly
from .serializers import (
    ProfileSerializer,
    BusinessProfileListSerializer,
    CustomerProfileListSerializer
)


class CustomerProfileListView(generics.ListAPIView):
    """
    Provides a GET-only endpoint that returns a list of all profiles
    marked with the 'customer' user type.
    """
    # We use our new, lean serializer
    serializer_class = CustomerProfileListSerializer

    # The user must be authenticated for access
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        This method overrides the default queryset to return only customer profiles.
        It ensures the view is filtered as required.
        """
        # We filter the basic QuerySet according to the type 'customer'.
        # Using the enum `Profile.UserType.CUSTOMER` is more robust than a hardcode string.
        # `select_related(‘user’)` is an important performance optimization.
        return Profile.objects.select_related('user').filter(type=Profile.UserType.CUSTOMER)


class BusinessProfileListView(generics.ListAPIView):
    """
    Provides a GET-only endpoint that returns a list of all profiles
    marked with the 'business' user type.
    """
    # We use our new, lean serializer
    serializer_class = BusinessProfileListSerializer

    # The user must be authenticated for access
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        This method overrides the default queryset to return only business profiles.
        It ensures the view is filtered as required.
        """
        # We filter the basic QuerySet according to the type ‘business’.
        # Using the enum `Profile.UserType.BUSINESS` is more robust than a hardcode string.
        # `select_related(‘user’)` is an important performance optimization.
        return Profile.objects.select_related('user').filter(type=Profile.UserType.BUSINESS)


class ProfileDetailView(generics.RetrieveUpdateAPIView):
    """
    Handles the detail endpoint for a user's profile.

    This view provides the following functionality:
    - GET: Retrieve the complete profile for a single user.
    - PATCH: Partially update the profile for a single user.
    - PUT: Fully update the profile for a single user.

    The profile is looked up using the associated User's primary key from the URL,
    not the Profile's own primary key.
    """

    # The base set of objects for this view.
    # .select_related('user') is a crucial performance optimization. It performs a
    # single, more complex SQL query to pre-fetch the related User object along
    # with the Profile, preventing additional database queries when the serializer
    # later accesses fields like 'user.username' or 'user.email'.
    queryset = Profile.objects.select_related('user').all()

    # Specifies the serializer class to use for validating and deserializing
    # input data, and for serializing the output response.
    serializer_class = ProfileSerializer

    # A list of permission classes that a user must satisfy to access the view.
    # Permissions are checked sequentially:
    # 1. `permissions.IsAuthenticated`: First, it ensures the user is logged in.
    #    If not, the request is immediately rejected with a 401 Unauthorized status.
    # 2. `IsOwnerOrReadOnly`: If the user is authenticated, this custom permission
    #    is checked next. It allows read-only access (GET) for any authenticated user
    #    but restricts write access (PATCH, PUT) only to the owner of the profile.
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    # The model field that should be used for the object lookup.
    # By setting it to 'user__pk', we instruct DRF to find the Profile instance
    # whose related 'user' has the primary key provided in the URL. This is the
    # key to making the URL `.../profile/{user_id}/` work correctly.
    lookup_field = 'user__pk'

    # The keyword argument from the URL that will be used for the lookup.
    # This must match the variable name in the URL pattern defined in `urls.py`.
    # For example, in `path('profile/<int:pk>/', ...), the name is 'pk'.
    lookup_url_kwarg = 'pk'
