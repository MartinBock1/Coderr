from rest_framework import serializers
from ..models import Order


class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    """
    A specialized serializer for updating only the 'status' of an Order.

    This serializer is intentionally limited to a single field to create a secure and specific
    endpoint for status changes (e.g., by a business user marking an order as 'completed'). It
    includes custom validation to prevent any other fields from being updated through its endpoint.
    """
    class Meta:
        """
        Metadata options for the OrderStatusUpdateSerializer.
        """
        model = Order
        # Explicitly define that only the 'status' field is managed by this serializer.
        fields = ['status']

    def validate(self, data):
        """
        Ensures that no fields other than those explicitly declared in this
        serializer are present in the request payload.

        DRF by default ignores extra fields. This validation enforces the
        strict requirement from the API documentation that such requests
        should fail.
        """
        # `self.initial_data` contains the raw data from the request,
        # before any processing.
        input_keys = set(self.initial_data.keys())
        
        # `self.fields` contains the fields that have been declared on this
        # serializer class (in this case, only 'status').
        allowed_keys = set(self.fields.keys())

        # Find any keys in the input that are not in the allowed set.
        extra_fields = input_keys - allowed_keys
        if extra_fields:
            # If extra fields exist, raise a validation error, which DRF
            # will turn into a 400 Bad Request response.
            raise serializers.ValidationError(
                f"Only the 'status' field can be updated. "
                f"Unrecognized fields provided: {', '.join(extra_fields)}"
            )
            
        return data


class CreateOrderSerializer(serializers.Serializer):
    """
    A simple serializer for initiating the creation of an Order.

    This serializer does not map directly to the Order model for input. Instead, it defines the
    expected payload for creating a new order, which in this case is the ID of a pre-existing
    "offer detail". The view logic will then use this ID to fetch the full offer details (price,
    features, etc.) and create the final Order object. This is a common pattern to ensure that
    orders are created based on valid, existing offers.
    """
    # An integer field to receive the primary key of the related offer detail.
    offer_detail_id = serializers.IntegerField()


class OrderSerializer(serializers.ModelSerializer):
    """
    A comprehensive serializer for the Order model.

    This is the main serializer used for representing a full Order object in API responses (e.g.,
    for list and detail views). It formats timestamps and defines which fields are read-only to
    protect sensitive or automatically-managed data.
    """
    # Format the output of timestamp fields to a consistent ISO 8601 format.
    # `read_only=True` because these are set automatically by the model.
    created_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%SZ", read_only=True)
    updated_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%SZ", read_only=True)

    class Meta:
        """Metadata options for the OrderSerializer."""
        # Link the serializer to the Order database model.
        model = Order
        # Specify all the fields from the Order model to be included in the API representation.
        fields = [
            'id',
            'customer_user',
            'business_user',
            'title',
            'revisions',
            'delivery_time_in_days',
            'price',
            'features',
            'offer_type',
            'status',
            'created_at',
            'updated_at'
        ]
        # Define fields that are included in the output but cannot be written to by the client.
        # This is a security measure to prevent users from arbitrarily changing crucial data like
        # who the customer/business is, the price, or the core features of the order after it has
        # been created.
        read_only_fields = [
            'customer_user',
            'business_user',
            'price',
            'offer_type',
            'features',
            'revisions',
            'delivery_time_in_days'
        ]
