from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth.models import User

# Import models from other apps
from reviews_app.models import Review
from offers_app.models import Offer
from profile_app.models import Profile


class BaseInfoAPITests(APITestCase):
    """
    Test suite for the `/api/base-info/` endpoint, which is part of the `platform_stats_app`.

    This suite verifies the correct aggregation of platform-wide statistics, covering both
    the initial state of an empty database and a scenario with populated data.
    """

    def setUp(self):
        """
        Prepares the environment for each test method.

        This defines the URL for the endpoint, which will be used in all subsequent tests.
        """
        # The URL name will now be scoped to our new app
        self.url = reverse('base-info')

    def test_base_info_on_empty_database(self):
        """
        Verifies the endpoint's behavior on an empty database.

        It ensures that all counts are zero and the average rating is correctly reported as `None`
        (which becomes `null` in the JSON response). This tests the initial state and edge cases.
        """
        # Act: Send a GET request to the endpoint without any data in the database.
        response = self.client.get(self.url)

        # Assert: The request should be successful with a 200 OK status.
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Arrange: Define the expected JSON response for an empty state.
        # The average of zero items is undefined, so `None` is the correct value.
        expected_data = {
            'review_count': 0,
            'average_rating': None,
            'business_profile_count': 0,
            'offer_count': 0
        }

        # Assert: The actual response data must match the expected structure and values.
        self.assertEqual(response.data, expected_data)

    def test_base_info_on_populated_database(self):
        """
        Verifies that the endpoint correctly aggregates and calculates statistics from a
        populated database.

        This test simulates a live environment by creating data across multiple, unrelated
        models (`User`, `Profile`, `Offer`, `Review`). It then calls the `/api/base-info/`
        endpoint and asserts that the returned aggregated values (counts and averages)
        exactly match the expected results calculated from the initial test data.
        """
        # --- Arrange: Create a set of test data across different models ---
        # 1. Create Users and set their corresponding Profile types. This step is
        #    crucial for testing the 'business_profile_count' aggregation.
        business_user1 = User.objects.create_user('business1')
        business_user2 = User.objects.create_user('business2')
        customer_user = User.objects.create_user('customer')

        # A Profile is created automatically via a signal. We update its `type`.
        business_user1.profile.type = Profile.UserType.BUSINESS
        business_user1.profile.save()
        
        business_user2.profile.type = Profile.UserType.BUSINESS
        business_user2.profile.save()
        
        customer_user.profile.type = Profile.UserType.CUSTOMER
        customer_user.profile.save()

        # 2. Create several offers from different business users to test 'offer_count'.
        Offer.objects.create(user=business_user1, title="Offer 1")
        Offer.objects.create(user=business_user1, title="Offer 2")
        Offer.objects.create(user=business_user2, title="Offer 3")

        # 3. Create reviews with different ratings to test 'review_count' and 'average_rating'.
        #    The expected average rating from this data is (5 + 4) / 2 = 4.5.
        Review.objects.create(business_user=business_user1, reviewer=customer_user, rating=5)
        Review.objects.create(business_user=business_user2, reviewer=customer_user, rating=4)

        # --- Act: Send a GET request to the endpoint ---
        response = self.client.get(self.url)

        # --- Assert: Verify the response ---
        # First, ensure the request itself was successful.
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Define the "ground truth": the dictionary of expected results based on the data
        # created in the Arrange step.
        expected_data = {
            'review_count': 2,
            'average_rating': 4.5,
            'business_profile_count': 2,
            'offer_count': 3
        }

        # The core assertion: the data returned by the API must exactly match our
        # pre-calculated expected values.
        self.assertEqual(response.data, expected_data)
