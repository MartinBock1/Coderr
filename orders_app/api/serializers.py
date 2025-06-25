from rest_framework import serializers
from ..models import Order

class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = [
            'id', 
            'customer_user', 
            'business_user', 
            'title',
            'revisions',
            'delivery_time_in_days',
            'price', 
            'features',
            'offer_type',
            'status', 
            'created_at', 
            'updated_at'
        ]