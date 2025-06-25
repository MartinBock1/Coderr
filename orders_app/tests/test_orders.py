from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth.models import User

from ..models import Order

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
        self.assertEqual(response.data['results'], [])
        self.assertEqual(response.data['count'], 0) 


# ====================================================================
# CLASS 2: Tests with preconfigured data
# ====================================================================
class OrderListAPITests(APITestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username='userA', password='password123')
        self.user_b = User.objects.create_user(username='userB', password='password123')
        self.user_c = User.objects.create_user(username='userC', password='password123')
        
        self.order1 = Order.objects.create(customer_user=self.user_a, business_user=self.user_b, title='Order 1', price=100)
        self.order2 = Order.objects.create(customer_user=self.user_c, business_user=self.user_a, title='Order 2', price=200)
        self.order3 = Order.objects.create(customer_user=self.user_b, business_user=self.user_c, title='Order 3', price=300)
    
    def test_user_only_sees_their_own_orders(self):
        url = reverse('order-list')
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)
        
        response_ids = {item['id'] for item in response.data['results']}
        expected_ids = {self.order1.id, self.order2.id}
        self.assertEqual(response_ids, expected_ids)

    def test_customer_can_retrieve_own_order_detail(self):
        url= reverse('order-detail', kwargs={'pk':self.order1.id})
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.order1.id)
        self.assertEqual(response.data['title'], 'Order 1')
        
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
        
        