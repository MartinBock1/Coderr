from rest_framework import serializers
from ..models import Review


class ReviewReadSerializer(serializers.ModelSerializer):
    """
    Serializes a Review object for read-only operations.

    This serializer is designed for API endpoints that display review data (e.g., list and detail
    GET requests). It includes all fields from the Review model, formats timestamps into a
    consistent ISO 8601 format, and represents ForeignKey relationships (like 'business_user' and
    'reviewer') by their primary key (ID).
    """
    # Format the output of timestamp fields to a consistent format for the API response.
    # `read_only=True` ensures these fields cannot be updated via the API, as they are managed
    # automatically by the model.
    created_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%SZ", read_only=True)
    updated_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%SZ", read_only=True)

    class Meta:
        model = Review
        # Defines all fields to be included in the serialized output.
        # By default, ForeignKey fields ('business_user', 'reviewer') are represented by their
        # integer primary key.
        fields = [
            'id',
            'business_user',
            'reviewer',
            'rating',
            'description',
            'created_at',
            'updated_at'
        ]


class ReviewCreateSerializer(serializers.ModelSerializer):
    """
    Handles the creation of a new Review instance.

    This serializer is used for write operations (POST requests). It defines the set of fields
    that a client can provide and includes custom validation logic to enforce business rules.
    """
    class Meta:
        model = Review
        # Defines the fields that are expected in the request payload.
        # 'reviewer' is intentionally excluded because it will be set automatically from the
        # authenticated user in the view, not provided by the client.
        fields = ['business_user', 'rating', 'description']

    def validate(self, data):
        """
        Performs custom cross-field validation.

        This method ensures that a user cannot submit a review for themselves, which is a critical
        business rule. It accesses the request user from the serializer's context.

        Args:
            data (dict): The dictionary of validated data.

        Raises:
            serializers.ValidationError: If the reviewer is the same as the business_user.

        Returns:
            dict: The validated data.
        """
        # The request object is passed into the serializer's context from the view.
        # This is the standard way to access request-specific information like the user.
        request = self.context.get('request')
        if not request:
             # This is a safeguard; in a standard DRF flow,
             # the context will always contain the request.
            return data

        # The user submitting the review.
        reviewer = request.user
        # The user being reviewed, from the incoming payload.
        business_user = data.get('business_user')

        # Enforce the business rule: a user cannot review themselves.
        if business_user == reviewer:
            raise serializers.ValidationError("You cannot create a review for yourself!")

        return data
