from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth.models import User


class LoginTests(APITestCase):
    """
    Test suite for the user login functionality.

    This class contains tests that cover various scenarios for the login API
    endpoint, including successful authentication, failed attempts with bad
    credentials, and requests with missing data.
    """
    
    def setUp(self):
        """
        Set up the test environment before each test method is run.

        This method creates a standard user in the test database, which will be
        used to test the login process.
        """
        self.user = User.objects.create_user(
            username='exampleUsername',
            email='example@mail.de',
            password='examplePassword'
        )

    def test_login_success(self):
        """
        Ensure a registered user can successfully log in with correct credentials.

        This test sends a POST request with a valid username and password to the
        login endpoint. It verifies that the response has a 200 OK status code
        and contains the expected data: an authentication token and user details.
        """
        url = reverse('login')
        data = {
            "username": "exampleUsername",
            "password": "examplePassword"
        }
        response = self.client.post(url, data, format='json')

        # Assert that the request was successful
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Assert that the response contains the expected keys and values
        self.assertIn('token', response.data)
        self.assertEqual(response.data['username'], 'exampleUsername')
        self.assertEqual(response.data['email'], 'example@mail.de')
        self.assertEqual(response.data['user_id'], self.user.id)

    def test_login_bad_credentials(self):
        """
        Ensure a login attempt with incorrect credentials fails.

        This test sends a POST request with a valid username but an incorrect password. It
        verifies that the response has a 400 Bad Request status code and contains the
        specific "non_field_errors" message indicating an authentication failure.
        """
        url = reverse('login')
        data = {
            "username": "exampleUsername",
            "password": "wrongPassword"
        }
        response = self.client.post(url, data, format='json')

        # Assert that the request was a bad request
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Assert that the correct error message is present
        self.assertIn('non_field_errors', response.data)
        expected_error = 'Unable to log in with provided credentials.'
        self.assertEqual(response.data['non_field_errors'][0], expected_error)

    def test_login_missing_fields(self):
        """
        Ensure a login attempt with missing credentials fails with validation errors.

        This test sends a POST request with empty strings for username and password. It verifies
        that the response has a 400 Bad Request status code and that the response body contains
        validation error details, indicating that the required fields were not provided correctly.
        """
        url = reverse('login')
        data = {
            "username": "",
            "password": ""
        }
        response = self.client.post(url, data, format='json')

        # Assert that the request was a bad request due to validation failure
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Assert that the response contains error details (is not empty)
        # A more specific check could be self.assertIn('username', response.data)
        self.assertTrue(len(response.data) > 0)
