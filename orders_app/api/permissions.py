from rest_framework.permissions import BasePermission
from profile_app.models import Profile


class IsBusinessUserAndOwner(BasePermission):
    """
    A custom DRF permission to check if a user is a 'business' type and the owner of an object.
    
    This permission is used for object-level authorization and ensures that the requesting user
    meets two strict criteria:
    
    1.  The user must have an associated `UserProfile` with its `type` field
        set to 'business'. This confirms their role in the system.
    2.  The user must be the same user referenced in the `business_user` field
        of the specific object instance being accessed (e.g., an Order).
        
    It is typically used in views to grant write access (like update or partial_update) only to the
    designated service provider for a resource.
    """

    def has_object_permission(self, request, view, obj):
        """
        Checks if the requesting user has permission to access the specific object 'obj'.

        Args:
            request: The incoming request object, containing the authenticated user.
            view: The view handling the request.
            obj: The database object instance that permission is being checked against.
                 For example, an instance of the `Order` model.

        Returns:
            bool: True if the user is a business user and the owner of the object, False otherwise.
        """
        try:
            # First condition: Verify the user has a profile and its type is 'business'.
            # This is wrapped in a try-except block to gracefully handle cases where
            # a user might not have a UserProfile object created yet.
            is_business = request.user.profile.type == 'business'
        except Profile.DoesNotExist:
            # If the user has no profile, they cannot be a business user. Deny permission
            # immediately.
            return False

        # Second condition: Verify that the user making the request is the same as the
        # user stored in the 'business_user' field of the object being checked.
        is_owner = obj.business_user == request.user

        # Permission is granted only if both conditions are met. The `and` operator ensures this.
        return is_business and is_owner
