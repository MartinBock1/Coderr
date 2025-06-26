from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.settings import api_settings
from django.contrib.auth.models import User

from ..models import Order
from offers_app.models import Offer, OfferDetail
from user_auth_app.models import UserProfile

# ====================================================================
# CLASS 1: Tests on an empty database
# ====================================================================


class OrderAPINoDataTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')

    def test_unauthenticated_user_cannot_access_orders(self):
        url = reverse('order-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticate_user_gets_empty_list_from_db(self):
        url = reverse('order-list')
        self.client.force_authenticate(user=self.user)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])


# ====================================================================
# CLASS 2: Tests with preconfigured data
# ====================================================================
class OrderListAPITests(APITestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username='userA', password='password123')
        self.user_b = User.objects.create_user(username='userB', password='password123')
        self.user_c = User.objects.create_user(username='userC', password='password123')

        self.order1 = Order.objects.create(
            customer_user=self.user_a, business_user=self.user_b, title='Order for A', price=100)
        self.order2 = Order.objects.create(
            customer_user=self.user_c, business_user=self.user_a, title='Order by A', price=200)
        self.order3 = Order.objects.create(
            customer_user=self.user_b, business_user=self.user_c, title='Order by B', price=300)
        Order.objects.create(customer_user=self.user_b, business_user=self.user_c,
                             title='Irrelevant Order', price=300)

    def test_user_only_sees_their_own_orders(self):

        url = reverse('order-list')
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        response_ids = {item['id'] for item in response.data}
        expected_ids = {self.order1.id, self.order2.id}
        self.assertEqual(response_ids, expected_ids)

    def test_customer_can_retrieve_own_order_detail(self):
        url = reverse('order-detail', kwargs={'pk': self.order1.id})
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.order1.id)

        created_at_str = response.data['created_at']
        self.assertTrue(created_at_str.endswith('Z'))
        self.assertNotIn('.', created_at_str)
        from datetime import datetime
        try:
            datetime.strptime(created_at_str, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            self.fail("created_at format is incorrect. Expected YYYY-MM-DDTHH:MM:SSZ")

    def test_business_partner_can_retrieve_own_order_detail(self):
        url = reverse('order-detail', kwargs={'pk': self.order2.id})
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.order2.id)

    def test_user_cannot_retrieve_other_users_order(self):
        url = reverse('order-detail', kwargs={'pk': self.order3.id})
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ====================================================================
# CLASS 3: Tests for creating (POST) orders
# ====================================================================
class OrderAPIPostTests(APITestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username='userA', password='password123')
        UserProfile.objects.create(user=self.user_a, type='customer')

        self.user_b = User.objects.create_user(username='userB', password='password123')
        UserProfile.objects.create(user=self.user_b, type='business')

        self.user_c = User.objects.create_user(username='userC', password='password123')
        UserProfile.objects.create(user=self.user_c, type='customer')

        self.main_offer = Offer.objects.create(
            user=self.user_b,
            title="Professional Logo Design"
        )

        self.offer_detail = OfferDetail.objects.create(
            offer=self.main_offer,
            title="Standard Package",
            price=250.00,
            delivery_time_in_days=7,
            revisions=5,
            features=["3 Concepts", "Vector File"],
            offer_type=OfferDetail.OfferType.STANDARD
        )

    def test_create_order_from_offer_detail_success(self):
        url = reverse('order-list')
        self.client.force_authenticate(user=self.user_a)
        request_data = {"offer_detail_id": self.offer_detail.id}
        initial_order_count = Order.objects.count()
        response = self.client.post(url, request_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), initial_order_count + 1)
        new_order = Order.objects.latest('id')
        self.assertEqual(new_order.business_user, self.main_offer.user)
        self.assertEqual(new_order.customer_user, self.user_a)
        self.assertEqual(new_order.title, self.offer_detail.title)
        self.assertEqual(float(new_order.price), float(self.offer_detail.price))
        self.assertEqual(new_order.revisions, self.offer_detail.revisions)

    def test_create_order_fails_with_invalid_offer_id(self):
        """
        Testet, ob ein 404 zurückgegeben wird, wenn die offer_detail_id nicht existiert.
        """
        url = reverse('order-list')
        self.client.force_authenticate(user=self.user_a)

        # Eine ID, die sicher nicht existiert
        invalid_id = 9999
        request_data = {"offer_detail_id": invalid_id}

        response = self.client.post(url, request_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_order_fails_without_offer_id(self):
        url = reverse('order-list')
        self.client.force_authenticate(user=self.user_a)
        request_data = {}
        response = self.client.post(url, request_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

# ====================================================================
# CLASS 4: Tests for updating (PATCH) orders
# ====================================================================


class OrderAPIPatchTests(APITestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username='customerA', password='password123')
        UserProfile.objects.create(user=self.user_a, type='customer')

        self.user_b = User.objects.create_user(username='businessB', password='password123')
        UserProfile.objects.create(user=self.user_b, type='business')

    def test_business_user_can_update_status(self):
        order = Order.objects.create(
            customer_user=self.user_a,
            business_user=self.user_b,
            title="Test Order",
            price=100
        )
        url = reverse('order-detail', kwargs={'pk': order.id})
        self.client.force_authenticate(user=self.user_b)

        response = self.client.patch(url, {'status': 'completed'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'completed')
        self.assertEqual(response.data['id'], order.id)
        self.assertIn('title', response.data)
        self.assertIn('price', response.data)

        order.refresh_from_db()
        self.assertEqual(order.status, 'completed')

    def test_customer_cannot_update_status(self):
        order = Order.objects.create(
            customer_user=self.user_a,
            business_user=self.user_b,
            title="Test Order",
            price=100
        )
        url = reverse('order-detail', kwargs={'pk': order.id})
        self.client.force_authenticate(user=self.user_a)

        response = self.client.patch(url, {'status': 'completed'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_business_user_cannot_update_other_fields(self):
        order = Order.objects.create(
            customer_user=self.user_a,
            business_user=self.user_b,
            title="Test Order",
            price=100.00
        )
        url = reverse('order-detail', kwargs={'pk': order.id})
        self.client.force_authenticate(user=self.user_b)

        update_data = {'status': 'completed', 'price': 999.00}
        response = self.client.patch(url, update_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        order.refresh_from_db()
        self.assertEqual(order.price, 100.00)
        self.assertEqual(order.status, 'in_progress')


# ====================================================================
# CLASS 5: Tests for DELETE endpoint
# ====================================================================
class OrderAPIDeleteTests(APITestCase):
    def setUp(self):
        self.customer_user = User.objects.create_user(username='customer', password='password123')
        UserProfile.objects.create(user=self.customer_user, type='customer')

        self.admin_user = User.objects.create_user(
            username='admin',
            password='password123',
            is_staff=True
        )
        UserProfile.objects.create(user=self.admin_user, type='business')

        self.order = Order.objects.create(
            customer_user=self.customer_user,
            business_user=self.admin_user,
            title="Order to be deleted",
            price=50
        )

    def test_admin_user_can_delete_order(self):
        url = reverse('order-detail', kwargs={'pk': self.order.id})
        self.client.force_authenticate(user=self.admin_user)

        initial_order_count = Order.objects.count()
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(Order.objects.count(), initial_order_count - 1)
        with self.assertRaises(Order.DoesNotExist):
            Order.objects.get(id=self.order.id)

    def test_normal_user_cannot_delete_order(self):
        url = reverse('order-detail', kwargs={'pk': self.order.id})
        self.client.force_authenticate(user=self.customer_user)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_cannot_delete_order(self):
        url = reverse('order-detail', kwargs={'pk': self.order.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ====================================================================
# CLASS 5: Tests for Order Count endpoint
# ====================================================================
class OrderCountViewTests(APITestCase):
    def setUp(self):
        self.request_user = User.objects.create_user(
            username='request_user',
            password='password123'
        )
        self.business_user = User.objects.create_user(
            username='business_user',
            password='password123'
        )
    
        for i in range(3):
            Order.objects.create(
                business_user=self.business_user,
                customer_user=self.request_user,
                status='in_progress',
                price=10
            )
        Order.objects.create(
            business_user=self.business_user,
            customer_user=self.request_user,
            status='completed',
            price=10
        )
        Order.objects.create(
            business_user=self.business_user,
            customer_user=self.request_user,
            status='cancelled',
            price=10
        )

    def test_get_order_count_success(self):
        url = reverse('order-count', kwargs={'business_user_id': self.business_user.id})
        self.client.force_authenticate(user=self.request_user)        
        response = self.client.get(url)        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'order_count': 3})

    def test_get_order_count_for_nonexistent_user(self):
        invalid_id = 9999
        url = reverse('order-count', kwargs={'business_user_id': invalid_id})
        self.client.force_authenticate(user=self.request_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
    def test_get_order_count_unauthenticated(self):
        url = reverse('order-count', kwargs={'business_user_id': self.business_user.id})       
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        
 # ====================================================================
# CLASS 5: Tests for Completed Order Count endpoint
# ====================================================================
class CompletedOrderCountViewTests(APITestCase):
    def setUp(self):
        self.request_user = User.objects.create_user(
            username='request_user',
            password='password123'
        )
        self.business_user = User.objects.create_user(
            username='business_user',
            password='password123'
        )
    
        for i in range(3):
            Order.objects.create(
                business_user=self.business_user,
                customer_user=self.request_user,
                status='completed',
                price=10
            )
        Order.objects.create(
            business_user=self.business_user,
            customer_user=self.request_user,
            status='in_progress',
            price=10
        )
        Order.objects.create(
            business_user=self.business_user,
            customer_user=self.request_user,
            status='cancelled',
            price=10
        )
        
    def test_get_completed_order_count_for_nonexistent_user(self):
        invalid_id = 9999
        url = reverse('completed-order-count', kwargs={'business_user_id': invalid_id})
        self.client.force_authenticate(user=self.request_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)   
    
    def test_get_completed_order_count_unauthenticated(self):
        url = reverse('completed-order-count', kwargs={'business_user_id': self.business_user.id})       
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)   
        