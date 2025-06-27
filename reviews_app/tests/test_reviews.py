from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth.models import User

from ..models import Review
from user_auth_app.models import UserProfile

# ====================================================================
# CLASS 1: Tests on an empty database
# ====================================================================
class ReviewAPINoDataTests(APITestCase):
    """
    Test suite for the Review API endpoints when the database is empty.
    These tests verify the initial state and basic authentication/authorization.
    """

    def setUp(self):
        """Set up a single generic user for authentication purposes."""
        self.user = User.objects.create_user(username='testuser', password='password123')

    def test_unauthenticated_user_cannot_access_reviews(self):
        """
        Verifies that an unauthenticated (anonymous) user receives a 401 Unauthorized
        error when trying to access the review list.
        """
        url = reverse('review-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_gets_empty_list_from_db(self):
        """
        Ensures an authenticated user receives a 200 OK status with an empty list `[]`
        when no reviews exist in the database.
        """
        url = reverse('review-list')
        # Authenticate the request as a valid user.
        self.client.force_authenticate(user=self.user)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # The response data should be an empty list since no reviews have been created.
        self.assertEqual(response.data, [])


# ====================================================================
# CLASS 2: Tests on a populated database
# ====================================================================
class ReviewAPIWithDataTests(APITestCase):
    """
    Test suite for the Review API endpoints when the database contains pre-existing data.
    These tests focus on filtering and retrieval.
    """

    def setUp(self):
        """
        Populates the database with multiple users and reviews to create a
        realistic test scenario for filtering.
        """
        self.business_user1 = User.objects.create_user(
            username='business1',
            password='password123'
        )
        self.business_user2 = User.objects.create_user(
            username='business2', password='password123'
        )
        self.reviewer1 = User.objects.create_user(
            username='reviewer1',
            password='password123'
        )
        self.reviewer2 = User.objects.create_user(
            username='reviewer2',
            password='password123'
        )

        # Create two reviews from the same reviewer for different businesses.
        self.review_low_rating = Review.objects.create(
            business_user=self.business_user1,
            reviewer=self.reviewer1,
            rating=4
        )
        self.review_high_rating = Review.objects.create(
            business_user=self.business_user2, reviewer=self.reviewer1,
            rating=5
        )

        # Authenticate all subsequent requests in this class as reviewer1.
        self.client.force_authenticate(user=self.reviewer1)

    def test_filter_reviews_by_business_user_id(self):
        """
        Verifies that the review list can be correctly filtered by the `business_user_id` query
        parameter.
        """
        url = reverse('review-list')
        # Request only reviews for business_user1.
        response = self.client.get(url, {'business_user_id': self.business_user1.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Assert that only one review is returned.
        self.assertEqual(len(response.data), 1)
        # Assert that the returned review is the correct one.
        self.assertEqual(response.data[0]['id'], self.review_low_rating.id)

    def test_filter_reviews_by_reviewer_id(self):
        """
        Verifies that the review list can be correctly filtered by the `reviewer_id` query
        parameter.
        """
        # Arrange: Create one more review from a different reviewer.
        Review.objects.create(
            business_user=self.business_user1,
            reviewer=self.reviewer2,
            rating=3
        )
        url = reverse('review-list')
        # Act: Request only reviews from reviewer2.
        response = self.client.get(url, {'reviewer_id': self.reviewer2.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Assert that only one review is returned.
        self.assertEqual(len(response.data), 1)
        # Assert that the returned review has the correct rating.
        self.assertEqual(response.data[0]['rating'], 3)


# ====================================================================
# CLASS 3: Tests for creating reviews
# ====================================================================
class ReviewCreateAPITests(APITestCase):
    """
    Test suite for creating new reviews via the `POST /api/reviews/` endpoint.
    Covers success cases, authorization rules, and validation logic.
    """

    def setUp(self):
        """
        Sets up users with distinct profiles ('customer', 'business') to test role-based
        permissions.
        """
        self.business_user = User.objects.create_user(
            username='business_owner',
            password='password123'
        )
        self.customer_user = User.objects.create_user(
            username='customer',
            password='password123'
        )
        self.another_business_user = User.objects.create_user(
            username='another_business',
            password='password123'
        )

        # Create UserProfile instances to assign roles.
        UserProfile.objects.create(user=self.business_user, type='business')
        UserProfile.objects.create(user=self.customer_user, type='customer')
        UserProfile.objects.create(user=self.another_business_user, type='business')

        self.url = reverse('review-list')  # The URL for creating reviews is the list endpoint.

    def test_unauthenticated_user_cannot_create_review(self):
        """
        Verifies that an unauthenticated user receives a 401 Unauthorized error
        when trying to create a review.
        """
        # NOTE: No client authentication is performed for this test.
        data = {'business_user': self.business_user.id,
                'rating': 5, 'description': "This should fail."}
        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        # Ensure no review object was created in the database.
        self.assertEqual(Review.objects.count(), 0)

    def test_customer_user_can_create_review(self):
        """
        Verifies that an authenticated user with a 'customer' profile can successfully create a
        review.
        """
        # Authenticate the request as the customer user.
        self.client.force_authenticate(user=self.customer_user)

        data = {'business_user': self.business_user.id,
                'rating': 5, 'description': "Excellent experience!"}
        response = self.client.post(self.url, data)

        # Assertions for a successful creation.
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Review.objects.count(), 1)

        review = Review.objects.first()
        self.assertEqual(review.reviewer, self.customer_user)
        self.assertEqual(review.business_user, self.business_user)
        self.assertEqual(response.data['rating'], 5)
        # Verify the reviewer ID is correctly set in the response, not from the payload.
        self.assertEqual(response.data['reviewer'], self.customer_user.id)

    def test_business_user_cannot_create_review(self):
        """
        Verifies that a user with a 'business' profile is denied permission (403 Forbidden) to
        create a review.
        """
        # Authenticate as a business user.
        self.client.force_authenticate(user=self.another_business_user)

        data = {
            'business_user': self.business_user.id,
            'rating': 4,
            'description': "This should not be allowed."
        }
        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Review.objects.count(), 0)

    def test_user_cannot_review_same_business_twice(self):
        """
        Verifies that a user receives a 403 Forbidden status when attempting to submit
        a second review for the same business.
        """
        # Arrange: Create an initial review.
        Review.objects.create(
            business_user=self.business_user,
            reviewer=self.customer_user,
            rating=4
        )

        # Act: Authenticate as the same customer and attempt to create a second review.
        self.client.force_authenticate(user=self.customer_user)
        data = {
            'business_user': self.business_user.id,
            'rating': 1,
            'description': "Trying to review again."
        }
        response = self.client.post(self.url, data)

        # Assert: The request is forbidden.
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # Assert: The number of reviews in the database has not changed.
        self.assertEqual(Review.objects.count(), 1)

    def test_user_cannot_review_themselves(self):
        """
        Verifies that a user receives a 400 Bad Request status when attempting
        to review themselves.
        """
        self.client.force_authenticate(user=self.customer_user)

        # The payload's 'business_user' is the same as the authenticated user.
        data = {
            'business_user': self.customer_user.id,
            'rating': 5,
            'description': "Reviewing myself"
        }
        response = self.client.post(self.url, data)

        # Assert: The request is invalid.
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Review.objects.count(), 0)
