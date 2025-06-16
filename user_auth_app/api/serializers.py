from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from user_auth_app.models import UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializes a UserProfile model instance for read operations.

    This serializer exposes the core fields of a UserProfile, primarily for displaying user
    details. It's not typically used for creation, as that logic is handled by the
    RegistrationSerializer.
    """
    class Meta:
        model = UserProfile
        fields = [
            'user',  # The ID of the associated Django User instance.
            'type'   # The role of the user, e.g., 'customer', 'business'.
        ]


class RegistrationSerializer(serializers.ModelSerializer):
    """
    Handles the registration of a new user.

    This serializer validates user input, confirms passwords, and creates both a new `User`
    instance and its associated `UserProfile`.

    Input Fields:
        - username (str): The desired username. Must be unique.
        - email (str): The user's email address. Must be unique.
        - password (str): The user's password.
        - repeated_password (str): The password for confirmation. Must match 'password'.
        - type (str): The type of user profile to create (e.g., 'customer').

    Output:
        - On successful validation and save, returns the newly created `User` instance.
    """
    repeated_password = serializers.CharField(
        style={'input_type': 'password'},
        write_only=True
    )
    type = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'repeated_password', 'type']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def validate(self, data):
        """
        Perform custom validation to ensure data integrity.

        Checks:
        1.  That the `password` and `repeated_password` fields match.
        2.  That the provided `email` is not already in use by another user.
        """
        if data['password'] != data['repeated_password']:
            raise serializers.ValidationError({'password': 'Passwords must match.'})

        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({'email': 'This email address already exists.'})

        return data

    def create(self, validated_data):
        """
        Create and save the new User and UserProfile instances.

        This method overrides the default `.create()` to handle the custom logic
        of creating two related model instances from the validated data. It uses
        Django's `create_user` helper to ensure the password is properly hashed.
        """
        # Create the User instance using the recommended helper method.
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )

        # Create the associated UserProfile instance
        UserProfile.objects.create(
            user=user,
            type=validated_data['type']
        )

        return user


class CustomAuthTokenSerializer(serializers.Serializer):
    """
    Authenticates a user based on username and password.

    This serializer is used for login endpoints. It takes a username and password, validates
    them using Django's authentication backend, and if successful, attaches the authenticated
    user object to the validated data.

    It does not create or update any models directly but is a crucial step before generating
    an authentication token.
    """
    username = serializers.CharField()
    password = serializers.CharField(
        label="Password",
        style={'input_type': 'password'},
        trim_whitespace=False
    )

    def validate(self, attrs):
        """
        Validate the provided username and password using Django's auth system.
        """
        username = attrs.get('username')
        password = attrs.get('password')

        if not (username and password):
            msg = 'Must include "username" and "password".'
            raise serializers.ValidationError(msg, code='authorization')

        # Pass the request from the view's context to the authenticate function.
        # This allows for more advanced authentication backends if needed.
        user = authenticate(
            request=self.context.get('request'),
            username=username,
            password=password
        )

        if not user:
            # Authentication failed. The user might be non-existent, inactive,
            # or the credentials might be wrong.
            msg = 'Unable to log in with provided credentials.'
            raise serializers.ValidationError(msg, code='authorization')

        # On success, the validated data dict is updated with the user object.
        attrs['user'] = user
        return attrs
