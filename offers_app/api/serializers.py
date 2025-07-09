from rest_framework import serializers
from django.contrib.auth.models import User
from django.db import transaction
from ..models import Offer, OfferDetail


class UserDetailSerializer(serializers.ModelSerializer):
    """
    Serializes a minimal set of User model fields for embedding within other serializers, like
    OfferListSerializer. This provides basic creator information without exposing sensitive user
    data.
    """
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username']


class OfferDetailReadSerializer(serializers.ModelSerializer):
    """
    Serializes an OfferDetail object for read-only purposes.

    This is the primary serializer for representing a single OfferDetail object in read-only
    contexts, such as in the `GET /api/offerdetails/{id}/` endpoint or when fully nested inside
    an OfferResponseSerializer.
    """

    class Meta:
        model = OfferDetail

        # These fields represent the public-facing data for an offer package.
        fields = [
            'id',
            'title',
            'revisions',
            'delivery_time_in_days',
            'price',
            'features',
            'offer_type',
        ]


class OfferDetailCreateSerializer(serializers.ModelSerializer):
    """
    Handles writable data for creating or updating an OfferDetail instance.

    This serializer is used for nested writes within the OfferCreateUpdateSerializer.
    It defines all the fields a user can provide when creating or modifying an offer package.
    """
    revisions = serializers.IntegerField(required=False, allow_null=True, min_value=-1, default=0)

    class Meta:
        model = OfferDetail

        # Defines all fields that can be written to by the client.
        fields = [
            'title',
            'price',
            'delivery_time_in_days',
            'description',
            'image',
            'revisions',
            'features',
            'offer_type'
        ]

    def validate_revisions(self, value):
        """
        Performs custom field-level validation for the 'revisions' field.

        This method is a hook provided by the Django REST Framework, automatically
        called for the `revisions` field during the .is_valid() process. Its
        purpose is to sanitize the input for the number of revisions.

        If the client omits the 'revisions' field in the request or explicitly sends
        `null`, the incoming `value` will be `None`. This validator intercepts that
        case and converts `None` into a default integer value of `0`. This ensures
        that a clean, non-null integer is always passed to the model instance,
        preventing potential database errors and simplifying model logic.

        Args:
            value (any): The incoming value for the 'revisions' field from the
                         request payload. This could be an integer, `None`, etc.

        Returns:
            int: The validated integer value for the revisions. Returns `0` if
                 the input `value` is `None`, otherwise returns the original value.
        """
        # If the value is None (e.g., field was omitted or sent as null),
        # convert it to 0.
        if value is None:
            return 0
        # Otherwise, return the value as is.
        return value


class OfferDetailUrlSerializer(serializers.HyperlinkedModelSerializer):
    """
    Serializes an OfferDetail to a lightweight representation with just its ID and URL.

    Used in list views (like OfferListSerializer) to avoid nesting large amounts of data, improving
    performance and keeping the API response lean.
    """
    # The view_name must match the basename provided to the router for the OfferDetailViewSet.
    url = serializers.HyperlinkedIdentityField(view_name='offerdetail-detail')

    class Meta:
        model = OfferDetail
        fields = ['id', 'url']


class OfferListSerializer(serializers.ModelSerializer):
    """
    Serializes Offer objects for the main list view (`GET /api/offers/`).

    This provides a summary representation of an offer, including calculated fields
    (min_price, min_delivery_time), basic user details, and URLs to the offer's detail packages
    instead of the full objects to keep the payload small.
    """
    # --- Calculated/Annotated Fields ---
    # These fields are read-only and expect the queryset to be annotated
    # by the view (e.g., with Min('details__price')).
    min_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    min_delivery_time = serializers.IntegerField(read_only=True, source='min_delivery_time_days')

    # --- Nested Serializers ---
    # Nests a simplified user object for display purposes.
    user_details = UserDetailSerializer(source='user', read_only=True)
    # Represents nested details as a list of URLs for efficiency in list views.
    details = OfferDetailUrlSerializer(many=True, read_only=True)

    # --- Formatted Fields ---
    # Formats the datetime to the ISO 8601 standard for API consistency.
    created_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%SZ", read_only=True)
    updated_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%SZ", read_only=True)

    class Meta:
        model = Offer
        fields = [
            'id',
            'user',  # The user's ID (ForeignKey)
            'title',
            'image',
            'description',
            'created_at',
            'updated_at',
            'details',  # The list of detail URLs
            'min_price',  # Annotated field
            'min_delivery_time',  # Annotated field
            'user_details',  # The nested user object
        ]


class OfferCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Handles the complex logic for creating a new Offer with its required OfferDetail packages, and
    for updating an existing Offer and its nested details.
    """
    # Accepts a list of nested JSON objects for the offer details upon creation/update.
    details = OfferDetailCreateSerializer(many=True)

    class Meta:
        model = Offer

        # Defines the fields that are writable from the API for the main Offer.
        fields = ['title', 'description', 'image', 'details']

    def validate_details(self, value):
        """
        Validates that exactly 3 detail packages are provided during creation.

        This validation is skipped during an update (PATCH/PUT), as a user might only want to
        update one or two packages.
        """
        # `self.instance` is None during a POST (create) request.
        # It holds the object instance during a PUT/PATCH (update) request.
        if self.instance is None:
            # This is a create operation, so enforce the rule.
            if len(value) != 3:
                raise serializers.ValidationError(
                    f"Exactly 3 detail packages are required for creation, but {len(value)} were provided."
                )

        # For update operations, we don't validate the count, as it's a partial update.
        return value

    def create(self, validated_data):
        """
        Handles the creation of an Offer and its nested OfferDetails as a single, atomic operation.

        This method is responsible for creating a parent `Offer` instance and its associated child
        `OfferDetail` instances from a single API request. It ensures data integrity by wrapping
        the database operations in a transaction. If the creation of the main offer or any of its
        details fails, the entire operation is rolled back, preventing orphaned data in the
        database.

        The process is as follows:
        1.  The nested 'details' data (a list of dictionaries) is separated from the main
        `validated_data` using `.pop()`.
        2.  A database transaction is started using `transaction.atomic()`.
        3.  The parent `Offer` object is created with the remaining top-level data.
        4.  The method then iterates through the list of detail data. For each item, it creates an
            `OfferDetail` instance, linking it back to the newly created parent `Offer`.
        5.  If all database operations within the block succeed, the transaction is committed.
            Otherwise, it is rolled back automatically upon an exception.

        Args:
            validated_data (dict): The validated data from the serializer. It is expected to
                                   contain the fields for the Offer model and a 'details' key
                                   holding a list of dictionaries, where each dictionary
                                   represents an OfferDetail.

        Returns:
            Offer: The newly created parent `Offer` instance, which can then be used to generate
                   the API response.
        """
        # Separate the nested details data from the main offer data.
        details_data = validated_data.pop('details')

        # Use a database transaction to ensure all or nothing is saved.
        with transaction.atomic():
            # Create the parent Offer instance with the top-level data.
            offer = Offer.objects.create(**validated_data)
            # Loop through the list of nested detail data.
            for detail_item in details_data:
                # Create each OfferDetail instance and link it to the parent Offer.
                OfferDetail.objects.create(offer=offer, **detail_item)

        # Return the newly created parent offer instance.
        return offer

    def update(self, instance, validated_data):
        """
        Handles partial updates for an Offer and its nested details.

        It updates the main offer fields and then intelligently updates the nested detail packages
        by matching them on their 'offer_type'.
        """
        # Update top-level Offer fields.
        instance.title = validated_data.get('title', instance.title)
        instance.description = validated_data.get('description', instance.description)
        instance.image = validated_data.get('image', instance.image)
        instance.save()

        # Check if detail data was provided in the PATCH/PUT request.
        details_data = validated_data.get('details')
        if details_data:
            # Create a dictionary of existing details keyed by 'offer_type' for efficient
            # lookup (O(1)).
            existing_details = {detail.offer_type: detail for detail in instance.details.all()}

            # Iterate through the incoming detail data to be updated.
            for detail_data in details_data:
                # Get the offer_type to identify which nested object to update.
                offer_type = detail_data.get('offer_type')
                if not offer_type:
                    raise serializers.ValidationError(
                        {"details": "Each detail to be updated must have an 'offer_type'."}
                    )

                # Find the matching existing detail instance.
                detail_instance = existing_details.get(str(offer_type))
                if not detail_instance:
                    raise serializers.ValidationError(
                        {"details":
                            f"A detail with offer_type '{offer_type}' does not exist for this offer."
                         }
                    )

                # Use the OfferDetailCreateSerializer to perform the update on the specific
                # detail instance. `partial=True` is crucial here, ensuring that only the provided
                # fields are updated.
                detail_serializer = OfferDetailCreateSerializer(
                    instance=detail_instance,
                    data=detail_data,
                    partial=True
                )
                detail_serializer.is_valid(raise_exception=True)
                detail_serializer.save()

        return instance


class OfferResponseSerializer(serializers.ModelSerializer):
    """
    Serializes a complete Offer instance for a detailed response.

    This is used after a `create` or `update` operation to return the full, updated object to the
    client, including fully-rendered nested details. It can also be used for the 'retrieve' action
    for a consistent, detailed view.
    """
    # Nests the full OfferDetail objects, not just their URLs.
    details = OfferDetailReadSerializer(many=True, read_only=True)

    # --- Read-only and nested fields, consistent with other serializers ---
    min_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    min_delivery_time = serializers.IntegerField(read_only=True, source='min_delivery_time_days')
    user_details = UserDetailSerializer(source='user', read_only=True)
    created_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%SZ", read_only=True)
    updated_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%SZ", read_only=True)

    class Meta:
        model = Offer
        fields = [
            'id',
            'user',
            'title',
            'image',
            'description',
            'created_at',
            'updated_at',
            'details',
            'min_price',
            'min_delivery_time',
            'user_details'
        ]


# NOTE: This serializer is a valid alternative for the retrieve action if you prefer
# to return only URLs for details, consistent with the list view.
# However, for API consistency, using OfferResponseSerializer for retrieve is often preferred.
class OfferRetrieveSerializer(serializers.ModelSerializer):
    """
    Serializes a single Offer instance for the retrieve (`GET /api/offers/{id}/`) action.

    It is similar to the list view, providing URLs to details rather than the full nested objects,
    which can be a valid design choice for certain use cases.
    """
    # --- Calculated/Annotated Fields ---
    min_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    min_delivery_time = serializers.IntegerField(read_only=True, source='min_delivery_time_days')

    # --- Nested Serializers ---
    # Represents nested details as URLs, consistent with the list view.
    details = OfferDetailUrlSerializer(many=True, read_only=True)

    # --- Formatted Fields ---
    # created_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%S.%fZ", read_only=True)
    # updated_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%S.%fZ", read_only=True)

    class Meta:
        model = Offer
        fields = [
            'id',
            'user',  # The user's ID
            'title',
            'image',
            'description',
            'created_at',
            'updated_at',
            'details',  # The list of detail URLs
            'min_price',
            'min_delivery_time'
        ]
