from rest_framework.permissions import BasePermission
from user_auth_app.models import UserProfile

class IsBusinessUserAndOwner(BasePermission):
    
    def has_object_permission(self, request, view, obj):
        try:
            is_business = request.user.userprofile.type == 'business'
        except UserProfile.DoesNotExist:
            return False

        is_owner = obj.business_user == request.user
        
        return is_business and is_owner