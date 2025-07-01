from rest_framework import serializers
from ..models import Review


class ReviewReadSerializer(serializers.ModelSerializer):
    """
    Serializer for the `Review` model, intended for read-only operations.

    This serializer is used to represent `Review` objects in API responses,
    for example, in list or detail views (GET requests). It includes a standard
    set of fields from the Review model.

    Foreign key relationships (`business_user`, `reviewer`) are represented
    by their primary keys (IDs), which is the default behavior. This makes the
    payload lightweight and is suitable when the client already has or can

    fetch the related user details separately.
    """    

    class Meta:
        """Meta class to configure the serializer's behavior."""
        
        # Specifies the Django model that this serializer is based on.
        model = Review
        # List of fields from the `Review` model to include in the output.
        # This explicit list ensures that only these fields are exposed
        # through the API endpoint using this serializer.
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
    
        Checks for:
        1. A user cannot review themselves.
        2. A user cannot submit more than one review for the same business.
        """
        # The request object is passed into the serializer's context from the view.
        # This is the standard way to access request-specific information like the user.
        request = self.context.get('request')
        if not request:
            # This is a safeguard; in a standard DRF flow,
            # the context will always contain the request.
            return data

        # The user submitting the review is the currently authenticated user.
        reviewer = request.user
        # The user being reviewed, from the incoming payload.
        business_user = data.get('business_user')

        # Enforce the business rule: a user cannot review themselves.
        if business_user == reviewer:
            raise serializers.ValidationError("You cannot create a review for yourself!")
        
        if Review.objects.filter(business_user=business_user, reviewer=reviewer).exists():
            # A ValidationError is automatically converted by DRF into a 400 Bad Request.
            raise serializers.ValidationError(
                "You have already submitted a review for this business."
        )

        return data


class ReviewUpdateSerializer(serializers.ModelSerializer):
    """
    Handles updating an existing Review instance.

    This serializer is intentionally limited to only the fields that are allowed to be edited
    ('rating' and 'description'). It ensures that critical, immutable fields like the reviewer or
    the reviewed business cannot be changed after creation, enhancing data integrity.
    """
    class Meta:
        """Configures the serializer's behavior."""
        model = Review
        # Only these fields will be accepted in a PATCH or PUT request. Any other fields
        # provided in the request body will be ignored by the serializer.
        # Only these fields will be accepted in a PATCH request.
        fields = ['rating', 'description']
