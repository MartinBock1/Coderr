from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from rest_framework.authtoken.models import Token

from user_auth_app.models import UserProfile
from user_auth_app.api.serializers import UserProfileSerializer, RegistrationSerializer
from django.contrib.auth.models import User


class RegistrationTests(APITestCase):

    def test_registration_success(self):
        # <-- Ersetze 'registration' durch den tatsächlichen URL-Namen
        url = reverse('registration')
        data = {
            "username": "exampleUsername",
            "email": "example@mail.de",
            "password": "examplePassword",
            "repeated_password": "examplePassword",
            "type": "customer"
        }

        response = self.client.post(url, data, format='json')

        # Prüfe Statuscode
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Prüfe Response-Felder
        self.assertIn('token', response.data)
        self.assertEqual(response.data['username'], data['username'])
        self.assertEqual(response.data['email'], data['email'])
        self.assertIn('user_id', response.data)

        # Prüfe, ob User in DB existiert
        from django.contrib.auth.models import User
        user_exists = User.objects.filter(username=data['username'], email=data['email']).exists()
        self.assertTrue(user_exists)

        # Optional: Prüfe UserProfile wurde angelegt mit dem 'type'
        from user_auth_app.models import UserProfile
        user = User.objects.get(username=data['username'])
        profile_exists = UserProfile.objects.filter(user=user, type=data['type']).exists()
        self.assertTrue(profile_exists)

    def test_registration_password_mismatch(self):
        url = reverse('registration')
        data = {
            "username": "exampleUsername",
            "email": "example@mail.de",
            "password": "examplePassword",
            "repeated_password": "differentPassword",  # absichtlich falsch
            "type": "customer"
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error'], 'Passwords do not match')
