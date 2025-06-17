from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from profile_app.models import Profile

# Helper function to dynamically generate the URL for the profile detail view.
# Using reverse() is more robust than hardcoding URLs, as it adapts to changes in your urls.py.


def PROFILE_DETAIL_URL(pk): return reverse('profile-detail', kwargs={'pk': pk})


BUSINESS_LIST_URL = reverse('business-profile-list')
CUSTOMER_LIST_URL = reverse('customer-profile-list')


class ProfileAPITests(APITestCase):
    """
    Test suite for the Profile API endpoints.

    This class contains a comprehensive set of tests for the profile-related
    API views, covering:
    - Core business logic (e.g., automatic profile creation via signals).
    - GET and PATCH requests for the detail view (`/api/profile/{pk}/`).
    - GET requests for the business list view (`/api/profiles/business/`).
    - Authentication and authorization rules for all endpoints.
    """

    def setUp(self):
        """
        Set up the initial state for each test method.

        This method runs before every single test function in this class. It creates
        two distinct users: one standard 'customer' and one 'business' user. This
        setup is crucial for testing various scenarios, such as a user accessing
        their own profile versus another's, and for filtering the business list.
        """
        # Create a standard user who will have the default 'customer' profile type.
        self.user1 = User.objects.create_user(
            username='testuser1',
            password='password123',
            email='user1@test.com'
        )

        # Create a second user who will be explicitly converted to a 'business' type.
        self.user2 = User.objects.create_user(
            username='testuser2',
            password='password123',
            email='user2@test.com'
        )

        # Create a second user who will be explicitly converted to a 'business' type.
        self.user3 = User.objects.create_user(
            username='testuser3',
            password='password123',
            email='user3@test.com'
        )

        # Manually change the profile type of user2 to 'business' for testing the list view.
        # This relies on the signal having already created the .profile attribute.
        self.user3.profile.type = Profile.UserType.BUSINESS
        self.user3.profile.save()

        # After creating users, verify that the signal handler worked correctly
        # and that both users now have an associated Profile object.
        self.assertIsNotNone(self.user1.profile)
        self.assertIsNotNone(self.user2.profile)
        self.assertIsNotNone(self.user3.profile)

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

    # === Tests for the Business Profile List View ===
    def test_get_business_list_unauthenticated(self):
        """
        Tests that an unauthenticated (anonymous) user cannot access the business profile list.

        This is a critical security test to ensure that the endpoint is properly
        protected by the `permissions.IsAuthenticated` class. An anonymous user
        should not be able to view any data and should be prompted to log in.
        The expected outcome is an HTTP 401 Unauthorized status code.
        """
        # Step 1: Make a GET request to the business list URL.
        # The `self.client` is used here without prior authentication,
        # which simulates a request from an anonymous, non-logged-in user.
        response = self.client.get(BUSINESS_LIST_URL)

        # Step 2: Assert that the response status code is 401 Unauthorized.
        # This is the standard HTTP status code for "authentication is required and
        # has failed or has not yet been provided." This confirms the permission
        # class on the view is working as intended.
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_business_list_authenticated(self):
        """
        Tests that an authenticated user can get the list of business profiles.

        This test verifies several key aspects of the business profile list endpoint:
        1.  The endpoint is accessible to authenticated users (returns 200 OK).
        2.  The response is a list containing only profiles of type 'business'.
        3.  The number of items in the list is correct.
        4.  The data for each item in the list is accurate.
        5.  Profiles of other types (e.g., 'customer') are correctly excluded.
        """
        # Step 1: Authenticate the test client as a regular 'customer' user (user1).
        # This demonstrates that any authenticated user, regardless of their own type,
        # should be able to view the list of businesses.
        self.client.force_authenticate(user=self.user1)

        # Step 2: Make a GET request to the business profile list endpoint.
        response = self.client.get(BUSINESS_LIST_URL)

        # Step 3: Assert the primary success condition.
        # The request should be successful because the user is authenticated.
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Step 4: Validate the structure and content of the response data.

        # Ensure the response data is a list, as expected for a list view.
        self.assertIsInstance(response.data, list)

        # Based on the `setUp` method, only one 'business' user was created (user3).
        # Therefore, the returned list should contain exactly one profile.
        self.assertEqual(len(response.data), 1)

        # Extract the first (and only) profile from the list for detailed inspection.
        business_profile_data = response.data[0]
        
        # Verify that the data in the response corresponds to the correct user (user3)
        # and has the correct type. This confirms the serializer and view filter are working.
        self.assertEqual(business_profile_data['username'], self.user3.username)
        self.assertEqual(business_profile_data['type'], Profile.UserType.BUSINESS)

        # Step 5: Final check to ensure that non-business users are correctly excluded.
        # We create a list of all usernames present in the response.
        usernames_in_response = [p['username'] for p in response.data]
        
        # Assert that the username of a known 'customer' user (user1) is not in this list,
        # confirming that the view's queryset filter is working correctly.
        self.assertNotIn(self.user1.username, usernames_in_response)

    # === Tests for the Customer Profile List View ===
    def test_get_customer_list_unauthenticated(self):
        """
        Tests that an unauthenticated (anonymous) user cannot access the customer profile list.

        This is a critical security test to ensure that the endpoint is properly
        protected by the `permissions.IsAuthenticated` class. An anonymous user
        should not be able to view any data and should be prompted to log in.
        The expected outcome is an HTTP 401 Unauthorized status code.
        """
        # Step 1: Make a GET request to the customer list URL.
        # The `self.client` is used here without prior authentication,
        # which simulates a request from an anonymous, non-logged-in user.
        response = self.client.get(CUSTOMER_LIST_URL)

        # Step 2: Assert that the response status code is 401 Unauthorized.
        # This is the standard HTTP status code for "authentication is required and
        # has failed or has not yet been provided." This confirms the permission
        # class on the view is working as intended.
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_customer_list_authenticated(self):
        """
        Tests that an authenticated user can get the list of customer profiles.

        This test verifies that the endpoint correctly returns a list containing
        only and all profiles of type 'customer'.
        """
        # Authenticate as any user (e.g. the business user user3)
        self.client.force_authenticate(user=self.user3)
        response = self.client.get(CUSTOMER_LIST_URL)

        # 1 Basic checks
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

        # 2. check the correct number
        # There should be exactly 2 customers (user1 and user2)
        self.assertEqual(len(response.data), 2)

        # 3. robust verification of the content (regardless of the order)
        # Create a list of usernames from the API response
        usernames_in_response = {p['username'] for p in response.data}

        # Create a set of expected usernames
        expected_usernames = {'testuser1', 'testuser2'}

        # Compare the two sets. This is the best way to check the
        # presence of all expected elements.
        self.assertEqual(usernames_in_response, expected_usernames)

        # 4. check that no unwanted elements are included
        # Make sure that the business user (user3) is NOT in the list.
        self.assertNotIn(self.user3.username, usernames_in_response)

        # 5. make sure that each entry in the list has the correct type
        for profile_data in response.data:
            self.assertEqual(profile_data['type'], Profile.UserType.CUSTOMER)
