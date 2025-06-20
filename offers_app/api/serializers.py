from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from offers_app.models import Offer, OfferDetail

# User = get_user_model()

class UserDetailSerializer(serializers.ModelSerializer):
    """A simple serializer for nested user details."""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username']

class OfferDetailUrlSerializer(serializers.HyperlinkedModelSerializer):
    """Serializer to represent OfferDetails just by their URL."""
    url = serializers.HyperlinkedIdentityField(view_name='offerdetail-detail') # Braucht einen ViewSet für OfferDetail

    class Meta:
        model = OfferDetail
        fields = ['id', 'url']
    

class OfferListSerializer(serializers.ModelSerializer):
    # Calculated fields - they are read-only and populated by the view's queryset annotation
    min_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    min_delivery_time = serializers.IntegerField(read_only=True, source='min_delivery_time_days')
    
    # Nested Serializer for user details
    user_details = UserDetailSerializer(source='user', read_only=True)
    
    # Related field for details
    details = OfferDetailUrlSerializer(many=True, read_only=True)
    
    created_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%SZ", read_only=True)
    updated_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%SZ", read_only=True)
    
    class Meta:
        model = Offer
        fields = [
            'id',
            'user',  # The user's ID
            'title',
            'image',
            'description',
            'created_at',
            'updated_at',
            'details', # The list of detail URLs
            'min_price',
            'min_delivery_time',
            'user_details', # The nested user object
        ]
