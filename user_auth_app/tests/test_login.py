from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token


class LoginTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='exampleUsername',
            email='example@mail.de',
            password='examplePassword'
        )

    def test_login_success(self):
        url = reverse('login')
        data = {
            "username": "exampleUsername",
            "password": "examplePassword"
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertEqual(response.data['username'], 'exampleUsername')
        self.assertEqual(response.data['email'], 'example@mail.de')
        self.assertEqual(response.data['user_id'], self.user.id)

    def test_login_bad_credentials(self):
        url = reverse('login')
        data = {
            "username": "exampleUsername",
            "password": "wrongPassword"
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)
        self.assertIn('Invalid username or password.', str(response.data['non_field_errors']))

    def test_login_missing_fields(self):
        url = reverse('login')
        data = {
            "username": "",
            "password": ""
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(len(response.data) > 0)
