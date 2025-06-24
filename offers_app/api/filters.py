import django_filters
from offers_app.models import Offer

class OfferFilter(django_filters.FilterSet):
    """
    A `FilterSet` for the `Offer` model to handle custom query parameter filtering.

    This class is designed to be used with `django-filter`'s `DjangoFilterBackend` in a Django
    REST Framework ViewSet. It defines the filtering logic for the offer list endpoint, enabling
    filtering on both direct model fields (like the user) and on dynamically calculated
    (annotated) values from the queryset.

    Available query parameters:
    - `creator_id`: Filters offers by the ID of the user who created them.
    - `min_price`: Filters offers with a minimum price greater than or equal to the value.
    - `max_delivery_time`: Filters offers with a delivery time less than or equal to the value.
    """
    # Filters for offers where the annotated `min_price` is greater than or equal to ('gte')
    # the provided value. The `field_name` explicitly targets the annotation created in the
    # ViewSet's `get_queryset` method.
    min_price = django_filters.NumberFilter(field_name="min_price", lookup_expr='gte')

    # Filters for offers where the annotated `min_delivery_time_days` is less than or equal to
    # ('lte') the provided value. This filter is named `max_delivery_time` for the API, but
    # it correctly maps to the `min_delivery_time_days` annotation from the queryset.
    max_delivery_time = django_filters.NumberFilter(field_name="min_delivery_time_days", lookup_expr='lte')
    
    # Filters for offers created by a specific user. This renames the filter from the model's
    # `user` field to the more explicit `creator_id` for API clarity. It targets the user's
    # primary key by traversing the relationship (`user__id`).
    creator_id = django_filters.NumberFilter(field_name="user__id")

    class Meta:
        """
        Meta options for the OfferFilter.
        """
        # Specifies that this FilterSet is built for the `Offer` model.
        model = Offer
        
        # Defines which of the declared filters are exposed in the API. Only the filter names
        # listed here will be usable as query parameters. This list makes the connection
        # between the class attributes above and the actual filtering mechanism.
        fields = ['creator_id', 'min_price', 'max_delivery_time']
