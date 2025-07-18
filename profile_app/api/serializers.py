from rest_framework import serializers
from django.contrib.auth.models import User
from ..models import Profile


class CustomerProfileListSerializer(serializers.ModelSerializer):
    """
    A lightweight, read-only serializer for listing customer profiles.

    This serializer is specifically designed for the customer list view. It flattens
    the data structure by combining essential fields from both the User and Profile
    models into a single, cohesive object for the API response.
    """
    # --- Fields from the linked User model ---
    # These fields are explicitly defined to traverse the 'user' relationship
    # and pull data directly from the associated User instance.
    user = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)

    # --- Fields from the Profile model (with special handling) ---

    # The profile's creation timestamp, which is renamed to 'uploaded_at' for the API output.
    # `source='created_at'`: Specifies that the data should come from the `created_at` model field.
    # `format="..."`: Enforces a specific ISO 8601 string format, omitting milliseconds and timezone.
    uploaded_at = serializers.DateTimeField(
        source='created_at', format="%Y-%m-%dT%H:%M:%S", read_only=True)

    # The full URL to the profile picture.
    # `source='file_url'`: This points to the `file_url` @property method on the Profile model,
    # ensuring that a complete URL is returned, not just a relative file path.
    file = serializers.CharField(source='file_url', read_only=True)

    class Meta:
        model = Profile

        # A list of all field names that should be included in the serialized output.
        # It's crucial that any field explicitly defined above is also included in this
        # list to be rendered in the final JSON response. The order here also
        # determines the order of fields in the response.
        fields = [
            'user',
            'username',
            'first_name',
            'last_name',
            'file',
            'uploaded_at',
            'working_hours',
            'type',
        ]


class BusinessProfileListSerializer(serializers.ModelSerializer):
    """
    A lightweight serializer for listing business profiles.
    It includes essential information from both the User and Profile models.
    """
    # Fields from the linked user model
    user = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)

    # URL of the profile picture from the property of the model
    file = serializers.CharField(source='file_url', read_only=True)

    class Meta:
        model = Profile
        # List of fields that exactly match the requirement
        fields = [
            'user',
            'username',
            'first_name',
            'last_name',
            'file',
            'location',
            'tel',
            'description',
            'working_hours',
            'type',
        ]


class ProfileSerializer(serializers.ModelSerializer):
    """
    Serializes Profile model instances for the API.

    This serializer combines fields from both the Profile model and its related User model to
    present a complete, flat structure for a user's profile. It is designed to handle both
    retrieving (GET) and updating (PATCH) data.
    """

    # --- Fields from the related User model ---
    # These fields are explicitly defined to pull data from the user relationship.

    # The user's username, read from the related User model.
    # The `source='user.username'` argument enables traversing the relationship.
    # Set to `read_only=True` to prevent it from being changed via this endpoint.
    username = serializers.CharField(source='user.username', read_only=True)

    # The user's email, also from the User model. This field is writable.
    email = serializers.EmailField(source='user.email')

    # User's first and last name.
    # `allow_blank=True` permits submitting an empty string, which is consistent
    # with the User model's behavior for these optional fields.
    first_name = serializers.CharField(source='user.first_name', allow_blank=True)
    last_name = serializers.CharField(source='user.last_name', allow_blank=True)

    # --- Fields from the Profile model (with special handling) ---

    file = serializers.ImageField(required=False, allow_null=True, use_url=True)

    # The user's unique ID.
    # The `source='user.id'` fetches the primary key from the related User object
    # and renames it to 'user' in the API output for clarity.
    user = serializers.IntegerField(source='user.id', read_only=True)

    # The profile's creation timestamp with custom formatting.
    # The `format` argument ensures a consistent ISO 8601 format
    # without milliseconds or timezone information (e.g., "2023-01-01T12:00:00").
    created_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%SZ", read_only=True)

    class Meta:
        """
        The Meta class links the serializer to a model and specifies its configuration.
        """
        model = Profile
        fields = [
            'user',
            'username',
            'first_name',
            'last_name',
            'file',
            'location',
            'tel',
            'description',
            'working_hours',
            'type',
            'email',
            'created_at'
        ]

        # This list is somewhat redundant here since `created_at` is already explicitly
        # defined as read-only, but it's the standard place to protect other model
        # fields from being written to if they were not explicitly defined.
        read_only_fields = ['created_at']

    def to_representation(self, instance):
        """
        Customizes the serializer's output representation for the instance.

        This method is a Django REST Framework hook that allows for the modification
        of the serialized data just before it is returned in an API response.
        Its primary purpose here is to ensure the output format of the 'file'
        field meets specific API requirements.

        The default behavior of a serialized `ImageField` is to return the full URL
        of the image if it exists, or `None` (which becomes `null` in JSON) if it
        does not. This method overrides the `null` case by converting it to an
        empty string (`''`), providing a more consistent and predictable data
        structure for API consumers.

        Args:
            instance (Model): The model instance that is being serialized (e.g., a `Profile`
            object).

        Returns:
            dict: The final, customized dictionary representation of the instance,
                  ready to be rendered into JSON.
        """
        # First, get the default representation from the parent class.
        # For an ImageField, this will correctly generate the full URL if a file exists.
        representation = super().to_representation(instance)

        # Check if the 'file' field in the generated representation is None.
        # This happens when the model's ImageField is empty.
        if representation.get('file') is None:
            # Replace 'None' with an empty string to meet API specifications.
            representation['file'] = ''

        # Return the modified representation.
        return representation

    def update(self, instance, validated_data):
        """
        Custom update logic to handle saving data to both the Profile and related User models.

        Args:
            instance (Profile): The Profile instance being updated.
            validated_data (dict): A dictionary of validated data from the request.

        Returns:
            Profile: The updated Profile instance.
        """
        # First, separate the data intended for the User model.
        # `pop` removes 'user' data from `validated_data` so the `super().update` call
        # won't try to process it. The `{}` default prevents an error if no user data is provided.
        user_data = validated_data.pop('user', {})
        user = instance.user

        # Safely update the User's fields. The `.get()` method with a default value
        # (the current value) ensures that only fields present in the PATCH request are updated.
        user.email = user_data.get('email', user.email)
        user.first_name = user_data.get('first_name', user.first_name)
        user.last_name = user_data.get('last_name', user.last_name)

        # Save the changes to the User model.
        user.save()

        # Now, call the parent class's `update` method with the remaining data.
        # This will handle saving all the fields that belong directly to the Profile model
        # (e.g., 'location', 'tel', 'description').
        instance = super().update(instance, validated_data)

        return instance
