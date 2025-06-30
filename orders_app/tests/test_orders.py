from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.settings import api_settings
from django.contrib.auth.models import User

from ..models import Order
from offers_app.models import Offer, OfferDetail
from profile_app.models import Profile

# ====================================================================
# CLASS 1: Tests on an empty database
# ====================================================================
class OrderAPINoDataTests(APITestCase):
    """
    Tests for the Order API endpoints when the database contains no Order data.
    These tests ensure the API behaves correctly for new or empty systems.
    """

    def setUp(self):
        """Set up a single user for authentication purposes."""
        self.user = User.objects.create_user(username='testuser', password='password123')

    def test_unauthenticated_user_cannot_access_orders(self):
        """Ensures that unauthenticated users receive a 401 Unauthorized error."""
        url = reverse('order-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_gets_empty_list_from_db(self):
        """
        Ensures an authenticated user receives a 200 OK with an empty list if no orders exist.
        """
        url = reverse('order-list')
        # Authenticate the request
        self.client.force_authenticate(user=self.user)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # The response data should be an empty list
        self.assertEqual(response.data, [])


# ====================================================================
# CLASS 2: Tests with preconfigured data
# ====================================================================
class OrderListAPITests(APITestCase):
    """
    Tests for GET (list and retrieve) functionality of the Order API using a pre-populated
    database to check permissions and data filtering.
    """

    def setUp(self):
        """Create multiple users and orders to test complex ownership and access rules."""
        self.user_a = User.objects.create_user(username='userA', password='password123')
        self.user_b = User.objects.create_user(username='userB', password='password123')
        self.user_c = User.objects.create_user(username='userC', password='password123')
        self.admin_user = User.objects.create_user(username='admin', password='password123', is_staff=True)

        # user_a is the customer
        self.order1 = Order.objects.create(
            customer_user=self.user_a, business_user=self.user_b, title='Order for A', price=100)
        # user_a is the business
        self.order2 = Order.objects.create(
            customer_user=self.user_c, business_user=self.user_a, title='Order by A', price=200)
        # user_a is not involved
        self.order3 = Order.objects.create(
            customer_user=self.user_b, business_user=self.user_c, title='Order by B', price=300)

    def test_user_only_sees_their_own_orders(self):
        """
        Verifies that a user can only see orders where they are either the customer or the
        business user.
        """
        url = reverse('order-list')
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # User A is involved in 2 orders
        self.assertEqual(len(response.data), 2)

        # Check that the correct order IDs are present in the response
        response_ids = {item['id'] for item in response.data}
        expected_ids = {self.order1.id, self.order2.id}
        self.assertEqual(response_ids, expected_ids)

    def test_customer_can_retrieve_own_order_detail(self):
        """
        Verifies a user can retrieve an order detail where they are the customer, and checks the
        format of the timestamp.
        """
        url = reverse('order-detail', kwargs={'pk': self.order1.id})
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.order1.id)

        # Check timestamp format (YYYY-MM-DDTHH:MM:SSZ)
        created_at_str = response.data['created_at']
        self.assertTrue(created_at_str.endswith('Z'))
        from datetime import datetime
        try:
            datetime.strptime(created_at_str, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            self.fail("created_at format is incorrect. Expected YYYY-MM-DDTHH:MM:SSZ")

    def test_business_partner_can_retrieve_own_order_detail(self):
        """Verifies a user can retrieve an order detail where they are the business user."""
        url = reverse('order-detail', kwargs={'pk': self.order2.id})
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.order2.id)

    def test_user_cannot_retrieve_other_users_order(self):
        """
        Ensures a user gets a 404 Not Found when trying to access an order they are not part of.
        """
        url = reverse('order-detail', kwargs={'pk': self.order3.id})
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_user_gets_only_their_own_orders_on_list_view(self):
        """
        Ensures that an admin user, when accessing the list view, only sees their own
        orders, not all orders on the platform.
        """
        # Create an order in which the admin is involved.
        Order.objects.create(customer_user=self.user_a, business_user=self.admin_user, title='Admin Order', price=500)
        
        url = reverse('order-list')
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # The admin should only see the one order they are involved in.
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Admin Order')

# ====================================================================
# CLASS 3: Tests for creating (POST) orders
# ====================================================================
class OrderAPIPostTests(APITestCase):
    """Tests for creating new orders via the POST endpoint."""

    def setUp(self):
        """
        Prepares a complete and realistic scenario for testing the creation of an `Order`.

        This method establishes all the necessary preconditions for an order to be placed.
        The key components and their roles in the test are:

        1.  A 'customer' User (`user_a`): This user will act as the buyer who initiates
            the order creation.
        2.  A 'business' User (`user_b`): This user acts as the seller who owns the offer
            being purchased.
        3.  An `Offer` and a specific `OfferDetail`: These represent the purchasable
            service. The `OfferDetail` is the crucial piece, as its ID will be sent in
            the POST request payload to create the order.

        This setup allows tests to simulate a customer purchasing a specific service from
        a business, validating the entire order creation workflow from request to database
        persistency.
        """
        # First, create the user who will act as the customer (the buyer).
        self.user_a = User.objects.create_user(username='userA', password='password123')
        # A Profile is created automatically via a post-save signal upon User creation.
        # We explicitly set its type to 'customer' to match the test's requirements.
        self.user_a.profile.type = Profile.UserType.CUSTOMER
        self.user_a.profile.save()

        # Next, create the user who will act as the business (the seller).
        self.user_b = User.objects.create_user(username='userB', password='password123')
        # We update the auto-created profile's type to 'business' for this user.
        self.user_b.profile.type = Profile.UserType.BUSINESS
        self.user_b.profile.save()

        # Create the parent Offer, which must be owned by the business user.
        self.main_offer = Offer.objects.create(
            user=self.user_b, title="Professional Logo Design")

        # This is the key object for the test. It represents the specific package
        # or service that the customer will purchase. Its ID will be used in the
        # POST request payload to create the order.
        self.offer_detail = OfferDetail.objects.create(
            offer=self.main_offer,
            title="Standard Package",
            price=250.00,
            delivery_time_in_days=7,
            revisions=5,
            features=["3 Concepts", "Vector File"],
            offer_type='standard'
        )

    def test_create_order_from_offer_detail_success(self):
        """Tests the successful creation of an order from a valid OfferDetail ID."""
        url = reverse('order-list')
        self.client.force_authenticate(user=self.user_a)
        request_data = {"offer_detail_id": self.offer_detail.id}
        initial_order_count = Order.objects.count()

        response = self.client.post(url, request_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Verify that a new order was added to the database
        self.assertEqual(Order.objects.count(), initial_order_count + 1)
        # Verify the new order's data matches the source offer detail
        new_order = Order.objects.latest('id')
        self.assertEqual(new_order.business_user, self.main_offer.user)
        self.assertEqual(new_order.customer_user, self.user_a)
        self.assertEqual(new_order.title, self.offer_detail.title)
        self.assertEqual(float(new_order.price), float(self.offer_detail.price))
        self.assertEqual(new_order.revisions, self.offer_detail.revisions)

    def test_create_order_fails_with_invalid_offer_id(self):
        """Tests that a 404 Not Found is returned if the offer_detail_id does not exist."""
        url = reverse('order-list')
        self.client.force_authenticate(user=self.user_a)
        # Use an ID that is guaranteed not to exist
        invalid_id = 9999
        request_data = {"offer_detail_id": invalid_id}

        response = self.client.post(url, request_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_order_fails_without_offer_id(self):
        """Tests that a 400 Bad Request is returned if the offer_detail_id is missing."""
        url = reverse('order-list')
        self.client.force_authenticate(user=self.user_a)
        request_data = {}  # Empty data
        response = self.client.post(url, request_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_business_user_cannot_create_order(self):
        """
        Ensures that a user with a 'business' profile is forbidden from creating an order.
        """
        url = reverse('order-list')
        # Authentifizieren Sie sich als Business-User (user_b)
        self.client.force_authenticate(user=self.user_b)
        request_data = {"offer_detail_id": self.offer_detail.id}

        response = self.client.post(url, request_data, format='json')

        # Erwarten Sie einen 403 Forbidden, da nur Kunden Bestellungen erstellen dürfen.
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

# ====================================================================
# CLASS 4: Tests for updating (PATCH) orders
# ====================================================================
class OrderAPIPatchTests(APITestCase):
    """Tests for updating orders via the PATCH endpoint (specifically for status updates)."""

    def setUp(self):
        """
        Prepares the environment to test the permission logic for updating an `Order`.

        This method establishes a specific scenario with all necessary preconditions to
        verify which users are authorized to modify an existing order. The key elements
        created are:

        1.  A 'customer' User (`user_a`): The buyer in the order, who should *not* have
            permission to update the order's status.
        2.  A 'business' User (`user_b`): The seller and designated "owner" of the order,
            who *should* have permission to update it.
        3.  An `Order` instance: The target resource for the update requests, linking the
            customer and business users.

        This setup allows tests to effectively validate role-based permission classes like
        `IsBusinessUserAndOwner`.
        """
        # Create the user who will act as the customer for the order.
        self.user_a = User.objects.create_user(username='customerA', password='password123')
        # A Profile is created automatically via a post-save signal. We ensure its
        # type is set to 'customer' for this test scenario.
        self.user_a.profile.type = Profile.UserType.CUSTOMER
        self.user_a.profile.save()

        # Create the user who will act as the business/provider for the order.
        # This user is the designated owner and should be the only one allowed to update.
        self.user_b = User.objects.create_user(username='businessB', password='password123')
        # We update the auto-created profile's type to 'business'.
        self.user_b.profile.type = Profile.UserType.BUSINESS
        self.user_b.profile.save()
        
        # Create the Order instance that will be the target of the update tests.
        # It explicitly links the customer and business users.
        self.order = Order.objects.create(
            customer_user=self.user_a,
            business_user=self.user_b,
            title="Test Order", price=100
        )

    def test_business_user_can_update_status(self):
        """Verifies that the business user who owns the order can update its status."""
        url = reverse('order-detail', kwargs={'pk': self.order.id})
        self.client.force_authenticate(user=self.user_b)
        response = self.client.patch(url, {'status': 'completed'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check that the response contains the full updated object
        self.assertEqual(response.data['status'], 'completed')
        self.assertEqual(response.data['id'], self.order.id)
        # Verify the database was actually updated
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'completed')

    def test_customer_cannot_update_status(self):
        """
        Ensures the customer user of an order cannot update its status (receives 403 Forbidden).
        """
        url = reverse('order-detail', kwargs={'pk': self.order.id})
        # Authenticate as the customer
        self.client.force_authenticate(user=self.user_a)
        response = self.client.patch(url, {'status': 'completed'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_business_user_cannot_update_other_fields(self):
        """
        Tests that a business user cannot update fields other than 'status' due to the specialized
        OrderStatusUpdateSerializer.
        """
        url = reverse('order-detail', kwargs={'pk': self.order.id})
        self.client.force_authenticate(user=self.user_b)
        # Attempt to update both status and a forbidden field (price)
        update_data = {'status': 'completed', 'price': 999.00}
        response = self.client.patch(url, update_data, format='json')

        # The custom validator in the serializer should reject this request.
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Verify that the original data in the database was not changed
        self.order.refresh_from_db()
        self.assertEqual(self.order.price, 100.00)
        self.assertEqual(self.order.status, 'in_progress')


# ====================================================================
# CLASS 5: Tests for DELETE endpoint
# ====================================================================
class OrderAPIDeleteTests(APITestCase):
    """Tests for deleting orders via the DELETE endpoint."""

    def setUp(self):
        """Creates a customer, an admin user, and an order to test deletion permissions."""
        self.customer_user = User.objects.create_user(username='customer', password='password123')
        self.business_user = User.objects.create_user(username='business', password='password123')
        self.admin_user = User.objects.create_user(
            username='admin', password='password123', is_staff=True, is_superuser=True)
        self.order = Order.objects.create(
            customer_user=self.customer_user,
            business_user=self.admin_user,
            title="Order to be deleted",
            price=50
        )

    def test_admin_user_can_delete_order(self):
        """Verifies that an admin user can successfully delete an order."""
        url = reverse('order-detail', kwargs={'pk': self.order.id})
        self.client.force_authenticate(user=self.admin_user)
        initial_order_count = Order.objects.count()

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Check that the order was actually removed from the database
        self.assertEqual(Order.objects.count(), initial_order_count - 1)
        with self.assertRaises(Order.DoesNotExist):
            Order.objects.get(id=self.order.id)

    def test_normal_user_cannot_delete_order(self):
        """Ensures that a non-admin user receives a 403 Forbidden when trying to delete."""
        url = reverse('order-detail', kwargs={'pk': self.order.id})
        self.client.force_authenticate(user=self.customer_user)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_cannot_delete_order(self):
        """Ensures an unauthenticated user receives a 401 Unauthorized."""
        url = reverse('order-detail', kwargs={'pk': self.order.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_can_delete_another_users_order(self):
        """
        Verifies that an admin can delete an order they are not personally involved in.
        This tests the special logic in get_object() for staff users.
        """
        url = reverse('order-detail', kwargs={'pk': self.order.id})
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Prüfen, ob die Bestellung wirklich weg ist.
        self.assertFalse(Order.objects.filter(id=self.order.id).exists())

# ====================================================================
# CLASS 6: Tests for Order Count endpoint
# ====================================================================
class OrderCountViewTests(APITestCase):
    """Tests for the custom `OrderCountView` endpoint."""

    def setUp(self):
        """Creates a business user and several orders with different statuses to test counting."""
        self.request_user = User.objects.create_user(
            username='request_user', password='password123')
        self.business_user = User.objects.create_user(
            username='business_user', password='password123')
        # Create 3 'in_progress' orders for the business user
        for _ in range(3):
            Order.objects.create(
                business_user=self.business_user,
                customer_user=self.request_user,
                status='in_progress',
                price=10
            )
        # Create orders with other statuses that should be ignored by this view
        Order.objects.create(
            business_user=self.business_user,
            customer_user=self.request_user,
            status='completed',
            price=10
        )

    def test_get_order_count_success(self):
        """
        Verifies the endpoint correctly counts and returns the number of 'in_progress' orders.
        """
        url = reverse('order-count', kwargs={'business_user_id': self.business_user.id})
        self.client.force_authenticate(user=self.request_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'order_count': 3})

    def test_get_order_count_for_nonexistent_user(self):
        """Ensures the endpoint returns a 404 Not Found when the user ID is invalid."""
        invalid_id = 9999
        url = reverse('order-count', kwargs={'business_user_id': invalid_id})
        self.client.force_authenticate(user=self.request_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_order_count_unauthenticated(self):
        """Ensures an unauthenticated request is rejected with a 401 Unauthorized."""
        url = reverse('order-count', kwargs={'business_user_id': self.business_user.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ====================================================================
# CLASS 7: Tests for Completed Order Count endpoint
# ====================================================================
class CompletedOrderCountViewTests(APITestCase):
    """Tests for the custom `CompletedOrderCountView` endpoint."""
    def setUp(self):
        """
        Creates a business user and several orders with different statuses to test counting.
        """
        self.request_user = User.objects.create_user(
            username='request_user', password='password123')
        self.business_user = User.objects.create_user(
            username='business_user', password='password123')
        # Create 3 'completed' orders
        for _ in range(3):
            Order.objects.create(
                business_user=self.business_user,
                customer_user=self.request_user,
                status='completed',
                price=10
            )
        # Create orders with other statuses that should be ignored
        Order.objects.create(
            business_user=self.business_user,
            customer_user=self.request_user,
            status='in_progress',
            price=10
        )

    def test_get_completed_order_count_success(self):
        """Verifies the endpoint correctly counts and returns the number of 'completed' orders."""
        url = reverse('completed-order-count', kwargs={'business_user_id': self.business_user.id})
        self.client.force_authenticate(user=self.request_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'completed_order_count': 3})

    def test_get_completed_order_count_for_nonexistent_user(self):
        """Ensures the endpoint returns a 404 Not Found when the user ID is invalid."""
        invalid_id = 9999
        url = reverse('completed-order-count', kwargs={'business_user_id': invalid_id})
        self.client.force_authenticate(user=self.request_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_completed_order_count_unauthenticated(self):
        """Ensures an unauthenticated request is rejected with a 401 Unauthorized."""
        url = reverse('completed-order-count', kwargs={'business_user_id': self.business_user.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
