from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from profile_app.models import Profile

# Helper function to dynamically generate the URL for the profile detail view.
# Using reverse() is more robust than hardcoding URLs, as it adapts to changes in your urls.py.


def PROFILE_DETAIL_URL(pk): return reverse('profile-detail', kwargs={'pk': pk})


class ProfileAPITests(APITestCase):
    """
    Test suite for the Profile API endpoint (/api/profile/{pk}/).
    Covers GET and PATCH methods, permissions, and core business logic.
    """

    def setUp(self):
        """
        This method runs before each individual test function. It sets up an initial state with
        two users, which allows for testing scenarios like accessing one's own profile vs. another
        user's profile.
        """
        self.user1 = User.objects.create_user(
            username='testuser1',
            password='password123',
            email='user1@test.com'
        )

        self.user2 = User.objects.create_user(
            username='testuser2',
            password='password123',
            email='user2@test.com'
        )

        # Verify that the signal handler for creating profiles is working as expected during setup.
        self.assertIsNotNone(self.user1.profile)
        self.assertIsNotNone(self.user2.profile)

    # === Test of core functionality and logic ===     
    def test_signal_creates_profile(self):
        """
        Tests that the post_save signal handler automatically creates a linked Profile object
        whenever a new User is created.
        """
        user_count = User.objects.count()
        profile_count = Profile.objects.count()
        
        # Create a new user, which should trigger the signal.
        new_user = User.objects.create_user(username='signaltestuser', password='password')
        
        # Check that the number of users and profiles has increased by one.
        self.assertEqual(User.objects.count(), user_count + 1)
        self.assertEqual(Profile.objects.count(), profile_count + 1)
        
        # Check that the new user has a 'profile' attribute and it's correctly linked.
        self.assertTrue(hasattr(new_user, 'profile'))
        self.assertEqual(new_user.profile.user, new_user)

    # === Tests for the GET request (retrieve profile) ===
    def test_get_profile_unauthenticated(self):
        """
        Tests that an unauthenticated request to the profile detail endpoint is rejected with a
        401 Unauthorized status.
        """
        url = PROFILE_DETAIL_URL(self.user1.pk)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_own_profile_authenticated(self):
        """
        Tests that an authenticated user can successfully retrieve their own profile.
        It also checks if the response data matches the user's details and the custom date format.
        """        
        # Authenticate the test client as user1.
        self.client.force_authenticate(user=self.user1)
        url = PROFILE_DETAIL_URL(self.user1.pk)
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify that the response contains the correct user data.
        self.assertEqual(response.data['user'], self.user1.pk)
        self.assertEqual(response.data['username'], self.user1.username)
        self.assertEqual(response.data['email'], self.user1.email)
        
        # Verify the custom datetime format (e.g., '2023-01-01T12:00:00').
        self.assertNotIn('Z', response.data['created_at'])  # Should not have timezone info.
        self.assertIn('T', response.data['created_at'])     # Should have 'T' separator.

    def test_get_other_users_profile(self):
        """
        Tests that an authenticated user can retrieve another user's profile. This is allowed by
        the `IsAuthenticated` permission for safe methods (GET).
        """
        self.client.force_authenticate(user=self.user1)
        url = PROFILE_DETAIL_URL(self.user2.pk)
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
         # Check that the data for the other user is returned.
        self.assertEqual(response.data['username'], self.user2.username)

    def test_get_profile_for_non_existent_user(self):
        """
        Tests that requesting a profile for a non-existent user ID results in a 404 Not Found
        error.
        """
        self.client.force_authenticate(user=self.user1)
        
        # Use a primary key that is highly unlikely to exist.
        url = PROFILE_DETAIL_URL(999)
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # === Tests for the PATCH request (edit profile) ===
    def test_update_own_profile(self):
        """
        Tests that a user can successfully update their own profile, including fields from both
        the User and Profile models.
        """
        self.client.force_authenticate(user=self.user1)
        url = PROFILE_DETAIL_URL(self.user1.pk)

        patch_data = {
            'first_name': 'NewFirstName',  # Field from the User model
            'location': 'New Location',    # Field from the Profile model
            'tel': '0987654321'            # Field from the Profile model
        }

        response = self.client.patch(url, data=patch_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check the response data immediately.
        self.assertEqual(response.data['first_name'], 'NewFirstName')
        self.assertEqual(response.data['location'], 'New Location')
        
        # Reload the objects from the database to ensure the changes were persisted.
        self.user1.refresh_from_db()
        self.user1.profile.refresh_from_db()
        
        self.assertEqual(self.user1.first_name, 'NewFirstName')
        self.assertEqual(self.user1.profile.location, 'New Location')

    def test_update_read_only_fields_is_ignored(self):
        """
        Tests that any attempt to update a read-only field (like 'username') via a PATCH request
        is silently ignored, while other writable fields are updated.
        """
        self.client.force_authenticate(user=self.user1)
        url = PROFILE_DETAIL_URL(self.user1.pk)
        original_username = self.user1.username

        patch_data = {
            'username': 'cannot_change_this',
            'location': 'Location Changed'
        }

        response = self.client.patch(url, data=patch_data, format='json')
        
        # The read-only username should not have changed in the response.
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # The writable location field should have changed.
        self.assertEqual(response.data['username'], original_username)
        self.assertEqual(response.data['location'], 'Location Changed')

    def test_update_other_users_profile_is_forbidden(self):
        """
        Tests that a user receives a 403 Forbidden status when attempting to update another user's
        profile, as enforced by the IsOwnerOrReadOnly permission.
        """
        # user1 attempts to modify user2's profile.
        self.client.force_authenticate(user=self.user1)
        url = PROFILE_DETAIL_URL(self.user2.pk)
        
        original_location = self.user2.profile.location
        patch_data = {'location': 'Hacked Location'}
        response = self.client.patch(url, data=patch_data, format='json')
        
        # The request should be forbidden.
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Verify that the data in the database remains unchanged.
        self.user2.profile.refresh_from_db()
        self.assertEqual(self.user2.profile.location, original_location)
        self.assertNotEqual(self.user2.profile.location, 'Hacked Location')
