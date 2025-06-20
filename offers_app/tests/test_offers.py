from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from offers_app.models import Offer, OfferDetail

User = get_user_model()

# ====================================================================
# CLASS 1: Tests on an empty database
# ====================================================================
class OfferAPINoDataTests(APITestCase):
    """
    Test suite for the Offer API endpoints in a clean state.

    This class groups tests that specifically verify the API's behavior when the database contains
    no `Offer` objects. It is designed to run without any data pre-population (e.g., via
    `setUpTestData`) to ensure the "empty" or "base" case is handled correctly.
    """

    def test_list_offers_endpoint_exists_and_returns_ok(self):
        """
        Ensures the offer list endpoint is configured and returns a 200 OK status.

        This is a basic "smoke test" to verify that the URL routing for the 'offer-list' view is
        set up correctly and that a simple GET request can be successfully processed, returning an
        HTTP 200 OK response.
        It confirms the endpoint is accessible before testing more complex logic.
        """
        # Resolve the URL for the offer list view. This checks if the URL name is valid.
        url = reverse('offer-list')
        
        # Make a GET request to the resolved URL using the test client.
        response = self.client.get(url)
        
        # Assert that the HTTP status code in the response is 200 (OK).
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_offers_returns_paginated_empty_list_when_no_offers(self):
        """
        Verifies the API returns a standard paginated structure when no offers exist.

        This test is crucial for ensuring API client stability. An API endpoint should always
        return a consistent data structure. For a list view, this means the paginated dictionary
        (`{'count': 0, 'results': [], ...}`) should be returned even if the database is empty,
        rather than a plain empty list (`[]`).

        This prevents potential `TypeError` exceptions on the client-side, which might always
        expect to access a `.results` property on the response.
        """
        # Get the URL for the offer list endpoint.
        url = reverse('offer-list')
        
        # Make a GET request to the endpoint.
        response = self.client.get(url)
        
        # --- Assertions for Pagination Structure ---
        # Verify that the standard pagination keys are present in the response data.
        self.assertIn('count', response.data)
        self.assertIn('results', response.data)
        
        # --- Assertions for Empty State ---
        # Check that the total count of items is correctly reported as 0.
        self.assertEqual(response.data['count'], 0)
        
        # Check that the list of results itself is empty.
        self.assertEqual(len(response.data['results']), 0)


# ====================================================================
# CLASS 2: Tests with preconfigured data
# ====================================================================
class OfferAPIWithDataTests(APITestCase):
    """
    Test suite for the Offer API endpoints that require a pre-populated database.

    This class groups tests for functionality like filtering, searching, and retrieving specific
    items. It utilizes the `setUpTestData` class method for efficient, one-time database setup,
    ensuring a consistent and known state for every test run within this suite.
    """
    @classmethod
    def setUpTestData(cls):
        """
        Sets up a predictable database state once for all tests in this class.

        This method is run by the Django test runner before any test methods in this class are
        executed. It's used to create a common set of objects that will be used across multiple
        tests, which is more performant than creating them in a `setUp` method for each test.

        The scenario created is:
        - Two distinct users (`user1`, `user2`).
        - Two `Offer` objects (`offer1`, `offer2`), each assigned to a different user.
        - Multiple `OfferDetail` records with varying prices and delivery times,
          allowing for testing of aggregation logic (min_price, min_delivery_time).

        The created objects are stored as class attributes (e.g., `cls.user1`) and are available
        in individual test methods via `self` (e.g., `self.user1`).
        """
        # Create two distinct users to test filtering and ownership.
        cls.user1 = User.objects.create_user(username='user1', first_name='U', last_name='One')
        cls.user2 = User.objects.create_user(username='user2', first_name='U', last_name='Two')

        # Create the first offer, associated with user1.
        # This offer has a minimum price of 100.00 and a minimum delivery time of 7 days.
        cls.offer1 = Offer.objects.create(
            user=cls.user1,
            title="Fast Website",
            description="A quick solution."
        )
        OfferDetail.objects.create(offer=cls.offer1, price=100.00, delivery_time_days=7)
        OfferDetail.objects.create(offer=cls.offer1, price=200.00, delivery_time_days=10)

        # Create the second offer, associated with user2.
        # This offer has a minimum price of 500.00 and a minimum delivery time of 20 days.
        cls.offer2 = Offer.objects.create(
            user=cls.user2,
            title="Complex App",
            description="An advanced solution."
        )
        OfferDetail.objects.create(offer=cls.offer2, price=500.00, delivery_time_days=20)

    def test_filter_by_creator_id(self):
        """
        Verifies that the offer list can be filtered by the creator's user ID.

        This test ensures that the `creator_id` query parameter functions correctly.
        It performs the following steps:
        1. Constructs a GET request to the offer list endpoint.
        2. Appends the `creator_id` query parameter, using the ID of `self.user1`.
        3. Asserts that the API response contains only the offer(s) created by
        that specific user.

        The test checks both the total count of the results and the content of the returned data
        to confirm the filter is being applied properly.
        """
        # Get the URL for the offer list endpoint.
        url = reverse('offer-list')
        
        # Send a GET request with a query parameter to filter by the creator's ID.
        response = self.client.get(url, {'creator_id': self.user1.id})
        
        # Assert that the title of the single returned offer is the one we expect
        # for the offer created by user1.
        self.assertEqual(response.data['results'][0]['title'], "Fast Website")
        
    def test_offer_list_data_structure_is_correct_ok(self):
        """
        Verifies the integrity of the data structure for a single serialized offer.

        This test acts as a "contract" for the API's output. It ensures that the JSON object for
        an offer contains all the expected fields, and that critical nested or calculated data is
        correctly represented.

        The process is as follows:
        1. Fetch the full, unfiltered list of all offers.
        2. Confirm the total count matches the number of offers created in the setup.
        3. Isolate a specific, known offer ("Fast Website") from the results to avoid dependencies
        on default ordering.
        4. Assert that the set of keys in the resulting JSON object matches the expected contract.
        5. Perform a specific data validation check on a nested field (the number of 'details') to
        ensure related data is handled correctly.
        """
        # Get the URL for the offer list endpoint.
        url = reverse('offer-list')
        
        # Make a GET request to retrieve all offers.
        response = self.client.get(url)
        
        # Basic sanity checks: the request should succeed and return all items.
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

        # To make the test robust, find a specific offer by its title rather than relying on the
        # order of results (which could change).
        result = next((item for item in response.data['results']
                       if item['title'] == 'Fast Website'), None)
        
        # Ensure the offer we want to inspect was actually found in the response.
        self.assertIsNotNone(result, "Offer 'Fast Website' not found in results")

        # Define the "contract": the exact set of keys we expect in the response.
        expected_keys = [
            'id',
            'user',
            'title',
            'image',
            'description',
            'created_at',
            'updated_at',
            'details',
            'min_price',
            'min_delivery_time',
            'user_details'
        ]
        # `assertCountEqual` checks that the keys are the same, regardless of order.
        self.assertCountEqual(result.keys(), expected_keys)
        
        # Verify that the nested 'details' list has the correct number of items, comparing it to
        # the source data in the database.
        self.assertEqual(len(result['details']), self.offer1.details.count())

    def test_filter_by_creator_id(self):
        """
        Verifies that the offer list can be filtered by the creator's user ID.

        This test ensures that the `creator_id` query parameter functions correctly.
        It performs the following steps:
        1. Constructs a GET request to the offer list endpoint.
        2. Appends the `creator_id` query parameter, using the ID of `self.user1`.
        3. Asserts that the API response contains only the offer(s) created by
        that specific user.

        The test checks both the total count of the results and the content of the returned data
        to confirm the filter is being applied properly.
        """
        # Get the URL for the offer list endpoint.
        url = reverse('offer-list')
        
        # Send a GET request with a query parameter to filter by the creator's ID.
        response = self.client.get(url, {'creator_id': self.user1.id})
        
        # Assert that the API correctly returns exactly one result, as user1
        # only created one offer in the test setup.
        self.assertEqual(response.data['count'], 1)
        
        # Assert that the title of the single returned offer is the one we expect for the offer
        # created by user1.
        self.assertEqual(response.data['results'][0]['title'], "Fast Website")

    def test_filter_by_min_price(self):
        """
        Verifies that the offer list can be filtered by a minimum price.

        This test ensures the `min_price` query parameter correctly filters out offers that are
        below the specified price threshold. It is particularly important because `min_price` is
        not a direct model field but an annotated value calculated from related `OfferDetail`
        objects.

        The test logic is:
        1. Send a GET request with `min_price=300`.
        2. Assert that only offers with a calculated minimum price of 300 or more are returned.
        3. Confirm the count of results and the specific content of the returned offer to ensure
        the filter works as expected.
        """
        # Get the URL for the offer list endpoint.
        url = reverse('offer-list')
        
        # Send a GET request with the min_price filter.
        # In our test data, offer1 (min_price=100) should be excluded,
        # and offer2 (min_price=500) should be included.
        response = self.client.get(url, {'min_price': 300})
        
        # Assert that only one offer meets the criteria.
        self.assertEqual(response.data['count'], 1)
        
        # Assert that the correct offer ("Complex App") is the one returned.
        self.assertEqual(response.data['results'][0]['title'], "Complex App")

    def test_filter_by_max_delivery_time(self):
        """
        Verifies the offer list can be filtered by a maximum delivery time.

        This test ensures the `max_delivery_time` query parameter correctly filters out offers
        that take longer to deliver than the specified threshold. This is a key test because
        `min_delivery_time` (the value being filtered) is not a direct model field but an
        annotated value calculated from related `OfferDetail` objects.

        The test logic involves:
        1. Sending a GET request with `max_delivery_time=15`.
        2. Asserting that only offers with a calculated minimum delivery time of 15 days or less
        are included in the response.
        3. Verifying both the result count and the content of the returned offer to confirm the
        filter's accuracy.
        """
        # Get the URL for the offer list endpoint.
        url = reverse('offer-list')
        
        # Send a GET request with the max_delivery_time filter.
        # In our test data, offer1 (min_delivery_time=7) should be included,
        # and offer2 (min_delivery_time=20) should be excluded.
        response = self.client.get(url, {'max_delivery_time': 15})
        
        # Assert that only one offer meets the criteria.
        self.assertEqual(response.data['count'], 1)
        
        # Assert that the correct offer ("Fast Website") is the one returned.
        self.assertEqual(response.data['results'][0]['title'], "Fast Website")

    def test_search_by_title_and_description(self):
        """
        Verifies the API's search functionality across multiple configured fields.

        This test ensures that the `search` query parameter, powered by DRF's `SearchFilter`,
        correctly queries the specified `search_fields` (in this case, `title` and `description`).

        It performs two distinct checks in sequence:
        1. A search for a term ('Fast') that exists only in the `title` of one offer.
        2. A separate search for a term ('advanced') that exists only in the `description` of
        another offer.

        Passing this test confirms that all configured search fields are being correctly indexed
        and queried.
        """
        # Get the URL for the offer list endpoint.
        url = reverse('offer-list')
        
        # 1. Search for a term present in the title of offer1.
        # We expect this to find the "Fast Website" offer.
        response = self.client.get(url, {'search': 'Fast'})
        self.assertEqual(response.data['count'], 1)
        
        # 2. Now, perform a separate search for a term in the description of offer2.
        # We expect this to find the "Complex App" offer with its "advanced solution" description.
        response = self.client.get(url, {'search': 'advanced'})
        self.assertEqual(response.data['count'], 1)

    def test_ordering_by_min_price(self):
        """
        Verifies that the offer list can be sorted by the calculated `min_price` field.

        This is a key test as it ensures DRF's `OrderingFilter` works correctly with annotated
        fields, which are calculated at query time and not stored directly on the model.

        It validates both ascending and descending order logic:
        1.  **Ascending (`min_price`):** Checks that the offer with the lowest minimum price
            ("Fast Website", price 100) appears first.
        2.  **Descending (`-min_price`):** Checks that the offer with the highest minimum price
            ("Complex App", price 500) appears first.
        """
        # Get the URL for the offer list endpoint.
        url = reverse('offer-list')
       
        # --- Test 1: Ascending Order ---
        # Send a GET request to order by min_price in ascending order.
        response = self.client.get(url, {'ordering': 'min_price'})
        results = response.data['results']
        
        # Assert that the first result is the cheaper offer.
        self.assertEqual(results[0]['title'], "Fast Website") # Price 100
        
        # Assert that the second result is the more expensive offer.
        self.assertEqual(results[1]['title'], "Complex App")  # Price 500

        # --- Test 2: Descending Order ---
        # Send a new GET request to order by min_price in descending order.
        response = self.client.get(url, {'ordering': '-min_price'})
        results = response.data['results']
        
        # Assert that the first result is now the more expensive offer.
        self.assertEqual(results[0]['title'], "Complex App")    # Price 500
        
        # Assert that the second result is now the cheaper offer.
        self.assertEqual(results[1]['title'], "Fast Website") # Price 100
