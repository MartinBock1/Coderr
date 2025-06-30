import time
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth.models import User

from ..models import Review
from profile_app.models import Profile

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

        This method establishes a specific data landscape to validate the API's filtering
        capabilities. The key aspects of the scenario are:
        - Two distinct 'business' users, allowing for tests that filter reviews for a
          specific business.
        - Two distinct 'reviewer' users, enabling tests that filter reviews by a
          specific author.
        - A scenario where one reviewer has written reviews for multiple businesses, which is
          essential for verifying that the filters correctly isolate the intended data.
        - A default authenticated user (`reviewer1`) for all tests in this class,
          simplifying the individual test methods.
        """
        # Create two users who will be the subjects of reviews.
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

        # Create a specific data relationship to test against: reviewer1 has authored
        # reviews for two different businesses. This is the core of the test setup.
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
        # This avoids having to repeat the authentication step in every test method.
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
        permissions for review creation.

        This method prepares a testing environment with users assigned specific roles to
        rigorously test the permission system for the `POST /api/reviews/` endpoint.

        The scenario includes:
        1.  A 'business' user (`business_user`): The intended target of a review.
        2.  A 'customer' user (`customer_user`): The authorized user who will attempt to
            create a review (the "happy path").
        3.  Another 'business' user (`another_business_user`): An unauthorized user who will
            also attempt to create a review, specifically to test the failure case for the
            `IsCustomerUser` permission.
        """
        # Create the user who will be the target of the review.
        self.business_user = User.objects.create_user(
            username='business_owner',
            password='password123'
        )
        # Create the user who is authorized to write reviews.
        self.customer_user = User.objects.create_user(
            username='customer',
            password='password123'
        )
        # Create another user with a 'business' profile to test permission denial.
        # This user should be blocked by the `IsCustomerUser` permission class.
        self.another_business_user = User.objects.create_user(
            username='another_business',
            password='password123'
        )

        # A Profile is automatically created for each User via a post-save signal.
        # We now update the 'type' of these auto-generated profiles to match the
        # roles required for our tests.
        # Assign the 'business' role to the target user.
        self.business_user.profile.type = Profile.UserType.BUSINESS
        self.business_user.profile.save()
        
        # Assign the 'customer' role to the authorized reviewer.
        self.customer_user.profile.type = Profile.UserType.CUSTOMER
        self.customer_user.profile.save()
        
        # Assign the 'business' role to the unauthorized reviewer.
        self.another_business_user.profile.type = Profile.UserType.BUSINESS
        self.another_business_user.profile.save()

        # The endpoint for creating reviews is the list view's URL.
        self.url = reverse('review-list')

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


# ====================================================================
# CLASS 4: Tests for updating reviews
# ====================================================================
class ReviewUpdateAPITests(APITestCase):
    """
    Test suite for updating existing reviews via `PATCH /api/reviews/{id}/`.

    Covers success cases for the owner, permission denials for non-owners and
    unauthenticated users, and validation for data and non-editable fields.
    """

    def setUp(self):
        """
        Sets up the initial state for all tests in this class.

        This includes creating users with different roles (owner vs. non-owner)
        and a target review object that will be updated in the tests.
        """
        # Use create_user to ensure passwords are properly hashed.
        self.reviewer_owner = User.objects.create(
            username='owner',
            password='password123'
        )
        self.reviewer_non_owner = User.objects.create(
            username='non_owner',
            password='password123'
        )
        self.business_user = User.objects.create(
            username='business',
            password='password123'
        )

        # Create the review that will be the target of our tests
        self.review = Review.objects.create(
            business_user=self.business_user,
            reviewer=self.reviewer_owner,
            rating=3,
            description="Initial description."
        )

        self.url = reverse('review-detail', kwargs={'pk': self.review.pk})

    def test_owner_can_update_review(self):
        """
        Verifies that the owner of a review can successfully update its rating and description.
        This is the "happy path" test case.
        """
        # Arrange: Authenticate the request as the review's owner.
        self.client.force_authenticate(user=self.reviewer_owner)

        # A small delay to ensure the `updated_at` timestamp will be different from `created_at`.
        time.sleep(0.01)

        update_data = {
            'rating': 5,
            'description': "Updated description!"
        }

        # Act: Send a PATCH request with the update data.
        response = self.client.patch(self.url, update_data)

        # Assert: The request was successful.
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert: The response body contains the updated data.
        self.assertEqual(response.data['rating'], 5)
        self.assertEqual(response.data['description'], "Updated description!")

        # Assert: The data was correctly saved to the database.
        self.review.refresh_from_db()
        self.assertEqual(self.review.rating, 5)
        self.assertNotEqual(self.review.created_at, self.review.updated_at)

    def test_non_owner_cannot_update_review(self):
        """
        Verifies that a user who is not the owner receives a 403 Forbidden error
        when trying to update a review.
        """
        # Arrange: Authenticate as a user who is NOT the owner of the review.
        self.client.force_authenticate(user=self.reviewer_non_owner)

        # Act: Attempt to send a PATCH request.
        update_data = {'rating': 1}
        response = self.client.patch(self.url, update_data)

        # Assert: The request was forbidden.
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_cannot_update_review(self):
        """Verifies that an unauthenticated user receives a 401 Unauthorized error."""
        # Arrange: No authentication is performed.
        # Act: Attempt to send a PATCH request.
        update_data = {'rating': 1}
        response = self.client.patch(self.url, update_data)

        # Assert: The request was unauthorized.
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cannot_update_forbidden_fields(self):
        """
        Verifies that critical, immutable fields like 'business_user' and 'reviewer'
        are silently ignored if included in an update request.
        """
        # Arrange: Authenticate as the owner.
        self.client.force_authenticate(user=self.reviewer_owner)

        # Arrange: Create another user to attempt to switch the `business_user` to.
        another_business_user = User.objects.create_user(username='otherbusiness')

        # Arrange: The payload includes a forbidden field ('business_user')
        # and an allowed one ('rating').
        update_data = {
            'business_user': another_business_user.id,  # Attempt to change a forbidden field
            'rating': 1  # Also include a valid field
        }

        # Act: Send the PATCH request.
        response = self.client.patch(self.url, update_data)

        # Assert: The request is still considered successful (200 OK) because invalid fields are
        # ignored by the serializer.
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert: Check the database to confirm the state of the object.
        self.review.refresh_from_db()
        # Assert that the forbidden field was NOT changed.
        self.assertEqual(self.review.business_user, self.business_user)
        # Assert that the allowed field WAS changed.
        self.assertEqual(self.review.rating, 1)

    def test_update_with_invalid_data(self):
        """
        Verifies that updating with invalid data (e.g., a rating > 5) results in a
        400 Bad Request error.
        """
        # Arrange: Authenticate as the owner.
        self.client.force_authenticate(user=self.reviewer_owner)

        # Arrange: The payload contains an invalid rating.
        update_data = {'rating': 10}

        # Act: Send the PATCH request.
        response = self.client.patch(self.url, update_data)

        # Assert: The server responded with a bad request error.
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_non_existent_review(self):
        """
        Verifies that trying to update a review that does not exist results
        in a 404 Not Found error.
        """
        # Arrange: Authenticate as any valid user.
        self.client.force_authenticate(user=self.reviewer_owner)

        # Arrange: Define a URL for a primary key that is guaranteed not to exist.
        non_existent_url = reverse('review-detail', kwargs={'pk': 9999})

        # Act: Send a PATCH request to the non-existent URL.
        response = self.client.patch(non_existent_url, {'rating': 1})

        # Assert: The server responded with a not found error.
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ====================================================================
# CLASS 5: Tests for deleting reviews
# ====================================================================
class ReviewDeleteAPITests(APITestCase):
    """
        Test suite for deleting existing reviews via `DELETE /api/reviews/{id}/`.

        This suite covers the success case for the review owner, permission denial for non-owners
        and unauthenticated users, and the handling of requests for non-existent reviews.
        """
    def setUp(self):
        """
        Sets up the initial state for all tests in this class.

        This includes creating users with different roles (owner vs. non-owner) and a target review
        object that will be the subject of the DELETE requests.
        """
        # Use create_user to ensure passwords are properly hashed.
        self.reviewer_owner = User.objects.create_user(
            username='owner',
            password='password123'
        )
        self.reviewer_non_owner = User.objects.create_user(
            username='non_owner',
            password='password123'
        )
        self.business_user = User.objects.create_user(
            username='business',
            password='password123'
        )

        # Create the review that will be the target of our tests
        self.review = Review.objects.create(
            business_user=self.business_user,
            reviewer=self.reviewer_owner,
            rating=3
        )

        self.url = reverse('review-detail', kwargs={'pk': self.review.pk})

    def test_owner_can_delete_review(self):
        """
        Verifies that the owner of a review can successfully delete it.
        This is the primary success case ("happy path").
        """
        # Arrange: Authenticate the request as the review's owner.
        self.client.force_authenticate(user=self.reviewer_owner)

        # Arrange: Confirm the review exists in the database before the deletion attempt.
        self.assertTrue(Review.objects.filter(pk=self.review.pk).exists())

        # Act: Send the DELETE request to the URL.
        response = self.client.delete(self.url)

        # Assert: The request was successful, indicated by a 204 No Content status.
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Assert: Verify that the review object has been permanently removed from the database.
        self.assertFalse(Review.objects.filter(pk=self.review.pk).exists())
        self.assertEqual(Review.objects.count(), 0)

    def test_non_owner_cannot_delete_review(self):
        """
        Verifies that a user who is not the owner receives a 403 Forbidden error
        when trying to delete a review.
        """
        # Arrange: Authenticate as a user who is NOT the owner of the review.
        self.client.force_authenticate(user=self.reviewer_non_owner)

        # Act: Attempt to send a DELETE request.
        response = self.client.delete(self.url)

        # Assert: The request was forbidden by the permission class.
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Assert: Verify the review was NOT deleted and still exists in the database.
        self.assertEqual(Review.objects.count(), 1)

    def test_unauthenticated_user_cannot_delete_review(self):
        """
        Verifies that an unauthenticated (anonymous) user receives a 401 Unauthorized error.
        """
        # Arrange: No client authentication is performed for this test.
        # Act: Attempt to send a DELETE request.
        response = self.client.delete(self.url)

        # Assert: The request was unauthorized.
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Assert: Verify the review was NOT deleted.
        self.assertEqual(Review.objects.count(), 1)

    def test_delete_non_existent_review(self):
        """
        Verifies that attempting to delete a review that does not exist results
        in a 404 Not Found error.
        """
        # Arrange: Authenticate as a valid user (the owner in this case).
        self.client.force_authenticate(user=self.reviewer_owner)

        # Arrange: Define a URL for a primary key that is guaranteed not to exist.
        non_existent_url = reverse('review-detail', kwargs={'pk': 9999})
        
        # Act: Send a DELETE request to the non-existent URL.
        response = self.client.delete(non_existent_url)

        # Assert: The server responded with a not found error.
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
