from rest_framework import permissions


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
    Custom permission to only allow users with a 'business' profile to act.

    This permission class implements a role-based access control check. It is designed for views
    where actions (like creating or modifying resources) are restricted to a specific type of
    user. In this case, only users identified as having a 'business' role are granted access.

    This class is intended for use in view-level permission checks, often in a view's
    `permission_classes` list or returned from `get_permissions()`. It assumes the User model has
    an attribute to identify the user's role.
    """
    # A custom error message that will be sent in the response if permission is denied.
    message = "You do not have permission to perform this action. \
               Only 'business' users are allowed."

    def has_permission(self, request, view):
        """
        Check if the user has permission to access the view at all.

        This method is called by DRF for any request to a view that uses this permission class. It
        runs before the view's main logic is executed.

        Args:
            request: The incoming HttpRequest object.
            view: The view that is handling the request.

        Returns:
            bool: True if permission is granted, False otherwise.
        """
        # First, we ensure that the user is authenticated. This check prevents
        # potential AttributeErrors when trying to access properties on an
        # AnonymousUser, which has no custom profile attributes.
        # The check for `request.user` handles cases where no user is associated at all.
        if not request.user or not request.user.is_authenticated:
            return False

        if hasattr(request.user, 'userprofile'):
            return request.user.userprofile.type == 'business'
        
        return False