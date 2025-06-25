from rest_framework import serializers
from ..models import Order


class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['status']
    
    def validate(self, data):
        allowed_fields = set(self.Meta.fields)
        input_keys = set(self.initial_data.keys())
        
        extra_fields = input_keys - allowed_fields
        if extra_fields:
            raise serializers.ValidationError(
                f"Unrecognized fields: {', '.join(extra_fields)}"
            )
        return data


class CreateOrderSerializer(serializers.Serializer):
    offer_detail_id = serializers.IntegerField()

    class Meta:
        fields = ['offer_detail_id']


class OrderSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%SZ", read_only=True)
    updated_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%SZ", read_only=True)

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
        read_only_fields = [
            'customer_user',
            'business_user',
            'price',
            'offer_type',
            'features',
            'revisions',
            'delivery_time_in_days'
        ]
