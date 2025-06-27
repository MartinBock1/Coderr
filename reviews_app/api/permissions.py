from rest_framework import permissions
from user_auth_app.models import UserProfile


class IsCustomerUser(permissions.BasePermission):
    """
    Custom permission to only allow users with a 'customer' profile to perform an action.

    This permission implements role-based access control by checking the `type` field on the user's
    associated `UserProfile`. It is typically used in a view's `get_permissions` method to restrict
    actions like 'create' to a specific user role.
    """
    # A custom error message that will be sent in the response if permission is denied.
    message = "Only users with a customer profile can create reviews."

    def has_permission(self, request, view):
        """
        Checks if the user has permission to access the view.

        This method is called by DRF for any request to a view using this permission.
        It first ensures the user is authenticated and then verifies that their
        associated `UserProfile` type is 'customer'.

        Args:
            request: The incoming HttpRequest object.
            view: The view that is handling the request.

        Returns:
            bool: True if permission is granted, False otherwise.
        """
        # First, ensure the user is authenticated. This is a crucial prerequisite
        # and prevents potential `AttributeError` exceptions when trying to access
        # `user.userprofile` on an `AnonymousUser`.
        if not request.user or not request.user.is_authenticated:
            return False

        # Attempt to access the related UserProfile and check its type.
        # This is wrapped in a try-except block to gracefully handle cases where a
        # User might exist without a corresponding UserProfile.
        try:
            # Grant permission only if the user's profile type is 'customer'.
            return request.user.userprofile.type == 'customer'
        except UserProfile.DoesNotExist:
            # If a UserProfile does not exist for the user, they cannot be a 'customer'.
            # Deny permission.
            return False


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow the owner of an object to edit it, while allowing read-only
    access for others.

    This is a common pattern for object-level security. It assumes that the object instance being
    checked has an attribute (in this case, `reviewer`) that links to a `User` instance.
    """

    def has_object_permission(self, request, view, obj):
        """
        Checks if the requesting user has permission to act upon the given object.

        This method is called by DRF for any request that operates on a specific
        object instance (e.g., retrieve, update, delete). It grants permission if the
        request method is safe (read-only) or if the requesting user is the owner
        of the object.

        Args:
            request: The incoming HttpRequest object.
            view: The view handling the request.
            obj: The database object that the request is targeting (e.g., a Review instance).

        Returns:
            bool: True if permission is granted, False otherwise.
        """
        # `SAFE_METHODS` is a tuple containing ('GET', 'HEAD', 'OPTIONS').
        # If the request method is one of these, it's considered a 'read' operation
        # and is always allowed for any user who has passed previous permission checks
        # (like `IsAuthenticated`).
        if request.method in permissions.SAFE_METHODS:
            return True

        # For write methods (PUT, PATCH, DELETE), permission is granted only if
        # the user making the request is the same user stored in the object's `reviewer` field.
        # This is the core ownership check.
        return obj.reviewer == request.user
