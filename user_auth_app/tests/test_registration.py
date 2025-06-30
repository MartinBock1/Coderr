from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse

from django.contrib.auth.models import User
from profile_app.models import Profile


class RegistrationTests(APITestCase):
    """
    Test suite for the user registration functionality.

    This class provides tests for the registration API endpoint, covering
    successful account creation and common failure scenarios like password
    mismatches.
    """

    def test_registration_success(self):
        """
        Ensure a new user can be registered successfully with valid data.

        This test verifies the entire registration flow:
        1. A POST request is sent to the registration endpoint with valid data.
        2. The response status code is checked for 201 Created.
        3. The response body is checked to ensure it contains the auth token and correct user details.
        4. The database is checked to confirm that both a `User` and a `Profile`
           object were correctly created.
        """
        url = reverse('registration')
        data = {
            "username": "exampleUsername",
            "email": "example@mail.de",
            "password": "examplePassword",
            "repeated_password": "examplePassword",
            "type": "customer"
        }

        response = self.client.post(url, data, format='json')

        # Check for a successful creation status code
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check the response body for expected fields
        self.assertIn('token', response.data)
        self.assertEqual(response.data['username'], data['username'])
        self.assertEqual(response.data['email'], data['email'])
        self.assertIn('user_id', response.data)

        # Verify that the user was actually created in the database
        user_exists = User.objects.filter(username=data['username'], email=data['email']).exists()
        self.assertTrue(user_exists)

        # Verify that the associated Profile was also created
        user = User.objects.get(username=data['username'])
        self.assertTrue(hasattr(user, 'profile'))
        self.assertEqual(user.profile.type, data['type'])

        # Verify that the profile was actually created in the database
        profile_exists = Profile.objects.filter(user=user, type=data['type']).exists()
        self.assertTrue(profile_exists)

    def test_registration_password_mismatch(self):
        """
        Ensure user registration fails if the passwords do not match.

        This test sends a POST request with a `password` and `repeated_password`
        that are different. It verifies that the API returns a 400 Bad Request
        status and a specific validation error message for the password field.
        """
        url = reverse('registration')
        data = {
            "username": "exampleUsername",
            "email": "example@mail.de",
            "password": "examplePassword",
            "repeated_password": "differentPassword",
            "type": "customer"
        }
        response = self.client.post(url, data, format='json')

        # Check for a bad request status code
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Check for the specific password validation error
        self.assertIn('password', response.data)
        self.assertEqual(response.data['password'][0], 'Passwords must match.')
