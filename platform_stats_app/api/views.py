from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db.models import Avg

# Import models from their respective apps to aggregate data
from reviews_app.models import Review
from offers_app.models import Offer
from user_auth_app.models import UserProfile


class BaseInfoView(APIView):
    """
    Provides a public, read-only endpoint for platform-wide statistics.

    This view is designed to be a "dashboard" or summary endpoint that is not tied to any single
    model. It aggregates data from multiple applications (reviews, offers, users) to present a
    high-level overview of the platform's activity. It is accessible without authentication.

    Endpoint:
        GET /api/base-info/
    """
    # This permission class makes the endpoint public and accessible to anyone,
    # including unauthenticated users.
    permission_classes = [AllowAny]

    def get(self, request, format=None):
        """
        Handles GET requests to calculate and return the platform's key statistics.

        This method performs several efficient, database-level queries to get the total counts of
        various resources and to calculate the average review rating. It then formats this data
        into a single JSON response.

        Args:
            request: The incoming HttpRequest object.
            format (str, optional): The requested response format (e.g., 'json', 'api').

        Returns:
            A DRF Response object containing the aggregated statistics and a 200 OK status.
        """
        # 1. Perform efficient database queries for counts.
        # .count() is a highly optimized operation that executes a `SELECT COUNT(*)`
        # query at the database level without retrieving the objects into memory.
        review_count = Review.objects.count()
        offer_count = Offer.objects.count()
        business_profile_count = UserProfile.objects.filter(type='business').count()

        # 2. Calculate the average rating using a database-level aggregation.
        # .aggregate() performs the calculation in the database and returns a dictionary.
        # e.g., {'average': 4.666...}
        avg_rating_result = Review.objects.aggregate(average=Avg('rating'))
        avg_rating = avg_rating_result.get('average')

        # 3. Handle rounding and the edge case of no reviews.
        # If no reviews exist, `avg_rating` will be `None`. This check ensures we
        # don't try to round `None`, which would cause an error.
        if avg_rating is not None:
            avg_rating = round(avg_rating, 1)

        # 4. Construct the response payload dictionary.
        # This dictionary will be serialized to JSON by the Response object.
        data = {
            'review_count': review_count,
            'average_rating': avg_rating,  # This will be `null` in JSON if no reviews exist.
            'business_profile_count': business_profile_count,
            'offer_count': offer_count,
        }

        # 5. Return the data wrapped in a DRF Response object with a success status.
        return Response(data, status=status.HTTP_200_OK)
