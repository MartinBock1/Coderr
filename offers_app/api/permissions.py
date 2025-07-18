from rest_framework import permissions
from profile_app.models import Profile


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.

    This permission class implements a common security pattern where:
    - Any authenticated user is allowed read-only access (e.g., GET, HEAD, OPTIONS).
    - Write permissions (e.g., POST, PUT, PATCH, DELETE) are restricted to the
      user who is associated with the object being accessed.

    This class is intended for use in object-level permission checks, typically
    in detail views where a single object instance is being evaluated.
    """
    def has_object_permission(self, request, view, obj):
        """
        Check if the requesting user has permission to act upon the object.

        This method is called by DRF for any request that operates on a specific object instance
        (e.g., retrieving, updating, or deleting).

        Args:
            request: The incoming HttpRequest object.
            view: The view that is handling the request.
            obj: The database object that the request is targeting (e.g., a Profile instance).

        Returns:
            bool: True if permission is granted, False otherwise.
        """
        # SAFE_METHODS is a tuple containing ('GET', 'HEAD', 'OPTIONS').
        # If the request method is one of these, it's considered a "read" operation
        # and is always allowed for any user who has passed previous permission checks
        # (like IsAuthenticated).
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # If the request method is not safe (e.g., it's a PATCH, PUT, or DELETE request),
        # we proceed to the ownership check.
        # This line compares the `user` associated with the object (`obj.user`)
        # with the user who is making the request (`request.user`).
        # Permission is only granted if these two users are the same instance.
        # For this to work, the model instance `obj` must have a `user` attribute.
        return obj.user == request.user

class IsBusinessUser(permissions.BasePermission):
    """
    Custom permission to only allow users with a 'business' profile to perform an action.

    This permission implements role-based access control (RBAC) by checking the `type` field on
    the user's associated `Profile` object. It's designed for use in views where certain actions,
    such as creating a new `Offer`, should be restricted to users who have been designated
    as a 'business' in the system.

    This is a view-level permission, meaning it runs for every request to a view that uses it,
    before the view's main logic is executed.
    """
    # A custom error message that DRF will include in the response body if this
    # permission check returns False.
    message = "You do not have permission to perform this action. \
               Only 'business' users are allowed."

    def has_permission(self, request, view):
        """
        Checks if the requesting user has permission to access the view.

        Args:
            request: The incoming HttpRequest object, which contains the authenticated user.
            view: The view that is handling the request.

        Returns:
            bool: True if the user is an authenticated 'business' user, False otherwise.
        """
        # First, ensure the user is authenticated. This is a critical prerequisite and
        # prevents potential `AttributeError` exceptions when trying to access `user.profile`
        # on an `AnonymousUser` (who has no profile).
        if not request.user or not request.user.is_authenticated:
            return False
        
        try:
            # Access the user's related profile via the `profile` reverse accessor.
            # The core logic: grant permission only if the profile's type is 'business'.
            return request.user.profile.type == Profile.UserType.BUSINESS
        except Profile.DoesNotExist:
            # If a Profile object does not exist for this user for any reason, they cannot
            # be a 'business' user. This gracefully handles the edge case and denies permission.
            return False
    