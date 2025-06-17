from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken

from .serializers import RegistrationSerializer, CustomAuthTokenSerializer


class RegistrationView(APIView):
    """
    Handles new user registration.

    This endpoint allows any unauthenticated user to create a new account.
    Upon successful registration, it creates a new User and its associated
    UserProfile, then returns an authentication token for immediate login.

    Endpoint:
        POST /api/register/

    Request Body:
        - username (str): The desired username.
        - email (str): The user's email address.
        - password (str): The user's password.
        - repeated_password (str): The password for confirmation.
        - type (str): The type of user profile (e.g., 'customer').

    Responses:
        - 201 Created: Registration was successful. Returns the auth token
          and basic user details.
          {
              "token": "your-auth-token",
              "username": "exampleUsername",
              "email": "example@mail.de",
              "user_id": 1
          }
        - 400 Bad Request: The provided data was invalid (e.g., passwords
          don't match, email already exists). The response body will contain
          details about the errors.
    """
    permission_classes = [AllowAny] # Allow any user (authenticated or not) to access this view.

    def post(self, request):
        """Processes the user registration request."""
        serializer = RegistrationSerializer(data=request.data)

        if serializer.is_valid():
            # The serializer's .save() method is a custom implementation that
            # creates both the User and UserProfile. It returns the user instance.
            saved_account = serializer.save()
            
            # Create or retrieve an authentication token for the new user.
            token, created = Token.objects.get_or_create(user=saved_account)
            
            # Prepare the response data.
            data = {
                'token': token.key,
                'username': saved_account.username,
                'email': saved_account.email,
                'user_id': saved_account.id
            }
            return Response(data, status=status.HTTP_201_CREATED)
        else:
            # If validation fails, return the errors provided by the serializer.
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomLoginView(ObtainAuthToken):
    """
    Handles user authentication and token generation.

    This view takes a username and password, authenticates the user, and
    returns an authentication token along with user details if the credentials
    are valid. It uses a custom serializer to control the authentication logic.

    Endpoint:
        POST /api/login/

    Request Body:
        - username (str): The user's username.
        - password (str): The user's password.

    Responses:
        - 200 OK: Authentication was successful. Returns the auth token
          and basic user details.
          {
              "token": "your-auth-token",
              "username": "exampleUsername",
              "email": "example@mail.de",
              "user_id": 1
          }
        - 400 Bad Request: Authentication failed (e.g., invalid credentials,
          missing fields). The response body will contain details about the error.
    """
    permission_classes = [AllowAny]  # Allow any user to attempt to log in.
    serializer_class = CustomAuthTokenSerializer # Use our custom serializer for validation.

    def post(self, request):
        """Processes the user login request."""
        # Note: We are overriding the default `post` method from `ObtainAuthToken`
        # to customize the success response format.
        serializer = self.serializer_class(
            data=request.data,
            context={'request': request} # Pass context to the serializer.
        )

        if serializer.is_valid():
            user = serializer.validated_data['user']
            token, created = Token.objects.get_or_create(user=user)
            
            # Prepare the custom response data.
            data = {
                'token': token.key,
                'username': user.username,
                'email': user.email,
                'user_id': user.id
            }
            return Response(data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
