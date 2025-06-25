from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.settings import api_settings
from django.contrib.auth.models import User

from ..models import Order
from offers_app.models import Offer, OfferDetail

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
    
    def test_user_only_sees_their_own_orders(self):
        order1 = Order.objects.create(customer_user=self.user_a, business_user=self.user_b, title='Order for A', price=100)
        order2 = Order.objects.create(customer_user=self.user_c, business_user=self.user_a, title='Order by A', price=200)
        Order.objects.create(customer_user=self.user_b, business_user=self.user_c, title='Irrelevant Order', price=300)
        
        url = reverse('order-list')
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        
        response_ids = {item['id'] for item in response.data}
        expected_ids = {order1.id, order2.id}
        self.assertEqual(response_ids, expected_ids)

    def test_customer_can_retrieve_own_order_detail(self):
        order1 = Order.objects.create(customer_user=self.user_a, business_user=self.user_b, title='Order for A', price=100)
        url= reverse('order-detail', kwargs={'pk':order1.id})
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], order1.id)
        
        created_at_str = response.data['created_at']
        self.assertTrue(created_at_str.endswith('Z'))
        self.assertNotIn('.', created_at_str)
        from datetime import datetime
        try:
            datetime.strptime(created_at_str, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            self.fail("created_at format is incorrect. Expected YYYY-MM-DDTHH:MM:SSZ")
        
    def test_business_partner_can_retrieve_own_order_detail(self):
        order2 = Order.objects.create(customer_user=self.user_c, business_user=self.user_a, title='Order by A', price=200)
        url = reverse('order-detail', kwargs={'pk': order2.id})
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], order2.id)
        
    def test_user_cannot_retrieve_other_users_order(self):
        order3 = Order.objects.create(customer_user=self.user_b, business_user=self.user_c, title='Order by B', price=300)
        url = reverse('order-detail', kwargs={'pk': order3.id})
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)  
        
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