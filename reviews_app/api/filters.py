import django_filters
from ..models import Review

class ReviewFilter(django_filters.FilterSet):
    """
    A FilterSet for the Review model to handle custom query parameter filtering.
    """
    # Renames the filter parameter from 'business_user' to 'business_user_id' for API clarity
    business_user_id = django_filters.NumberFilter(field_name="business_user__id")
    
    # Renames the filter parameter from 'reviewer' to 'reviewer_id' for API clarity
    reviewer_id = django_filters.NumberFilter(field_name="reviewer__id")
    
    class Meta:
        model = Review
        # The list of filter names exposed in the API
        fields = ['business_user_id', 'reviewer_id']