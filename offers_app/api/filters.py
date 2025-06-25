import django_filters
from offers_app.models import Offer


class OfferFilter(django_filters.FilterSet):
    """
    A `FilterSet` for the `Offer` model to handle custom query parameter filtering.

    This class is used with `django-filter`'s `DjangoFilterBackend` in a DRF ViewSet to provide a
    powerful filtering interface for the offer list endpoint. It enables filtering on both direct
    model relationships (like the user) and on dynamically calculated (annotated) values from the
    queryset.

    Attributes:
        min_price (NumberFilter): Filters for offers with a `min_price` gte the value.
        max_delivery_time (NumberFilter): Filters for offers with a delivery time
                                          lte the value.
        creator_id (NumberFilter): Filters offers by the ID of the creating user.
    """
    # Filters for offers where the annotated `min_price` is greater than or equal to ('gte')
    # the provided value. The `field_name` explicitly targets the annotation created in the
    # ViewSet's `get_queryset` method.
    min_price = django_filters.NumberFilter(field_name="min_price", lookup_expr='gte')

    # Filters for offers where the annotated `min_delivery_time_days` is less than or equal to
    # ('lte') the provided value. This filter is named `max_delivery_time` for the API, but
    # it correctly maps to the `min_delivery_time_days` annotation from the queryset.
    max_delivery_time = django_filters.NumberFilter(
        field_name="min_delivery_time_days", lookup_expr='lte'
    )

    # Filters for offers created by a specific user. This renames the filter from the model's
    # `user` field to the more explicit `creator_id` for API clarity. It targets the user's
    # primary key by traversing the relationship (`user__id`).
    creator_id = django_filters.NumberFilter(field_name="user__id")

    class Meta:
        """
        Configures the `OfferFilter` by linking it to a model and specifying which of its filter
        definitions are active and exposed in the API.
        """
        # Specifies that this FilterSet is built for the `Offer` model.
        model = Offer

        # A list of filter names to be exposed in the API. Only the filter names defined as
        # attributes on this class and listed here will be usable as query parameters. This
        # connects the class attributes above to the filtering engine.
        fields = ['creator_id', 'min_price', 'max_delivery_time']
