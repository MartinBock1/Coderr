import time

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.settings import api_settings
from django.contrib.auth.models import User

from ..models import Review

# ====================================================================
# CLASS 1: Tests on an empty database
# ====================================================================


class ReviewAPINoDataTests(APITestCase):
    def setUp(self):
        """Set up a single user for authentication purposes."""
        self.user = User.objects.create_user(username='testuser', password='password123')

    def test_unauthenticated_user_cannot_access_reviews(self):
        """Ensures that unauthenticated users receive a 401 Unauthorized error."""
        url = reverse('review-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_gets_empty_list_from_db(self):
        """
        Ensures an authenticated user receives a 200 OK with an empty list if no reviews exist.
        """
        url = reverse('review-list')
        # Authenticate the request
        self.client.force_authenticate(user=self.user)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # The response data should be an empty list
        self.assertEqual(response.data, [])


# ====================================================================
# CLASS 2: Tests on a populated database
# ====================================================================
class ReviewAPIWithDataTests(APITestCase):
    def setUp(self):
        """
        Set up users and reviews for testing in a way that decouples creation order
        from rating order.
        """
        self.business_user1 = User.objects.create_user(
            username='business1',
            password='password123'
        )
        self.business_user2 = User.objects.create_user(
            username='business2',
            password='password123'
        )
        self.reviewer1 = User.objects.create_user(
            username='reviewer1',
            password='password123'
        )
        self.reviewer2 = User.objects.create_user(
            username='reviewer2',
            password='password123'
        )

        self.review_low_rating = Review.objects.create(
            business_user=self.business_user1,
            reviewer=self.reviewer1,
            rating=4
        )
        time.sleep(0.01)
        
        self.review_high_rating = Review.objects.create(
            business_user=self.business_user2,
            reviewer=self.reviewer1,
            rating=5
        )
        self.client.force_authenticate(user=self.reviewer1)

    def test_filter_reviews_by_business_user_id(self):
        """Ensures the list can be filtered by the business_user_id."""
        url = reverse('review-list')
        response = self.client.get(url, {'business_user_id': self.business_user1.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'],self.review_low_rating.id)

    def test_filter_reviews_by_reviewer_id(self):
        """Ensures the list can be filtered by the reviewer_id."""
        # Create one more review from another reviewer
        Review.objects.create(
            business_user=self.business_user1,
            reviewer=self.reviewer2,
            rating=3
        )
        url = reverse('review-list')
        response = self.client.get(url, {'reviewer_id': self.reviewer2.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['rating'], 3)
        
    