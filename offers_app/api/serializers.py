from rest_framework import serializers, status
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from offers_app.models import Offer, OfferDetail

# User = get_user_model()


class UserDetailSerializer(serializers.ModelSerializer):
    """A simple serializer for nested user details."""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username']

class OfferDetailReadSerializer(serializers.ModelSerializer):
    """
    Serializes a complete OfferDetail object for read operations, including all its fields.
    """
    class Meta:
        model = OfferDetail
        fields = [
            'id', 
            'title', 
            'price', 
            'delivery_time_days', 
            # Fügen Sie hier alle anderen Felder aus Ihrem OfferDetail-Modell hinzu,
            # z.B. 'revisions', 'features', 'offer_type', 'description'
        ]

class OfferResponseSerializer(serializers.ModelSerializer):
    """
    Serializer for the response after creating/retrieving a single Offer.
    It's similar to the ListSerializer but includes full nested details.
    """
    # Verwenden Sie den vollständigen Detail-Serializer
    details = OfferDetailReadSerializer(many=True, read_only=True)
    
    # Die restlichen Felder sind identisch mit OfferListSerializer
    min_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    min_delivery_time = serializers.IntegerField(read_only=True, source='min_delivery_time_days')
    user_details = UserDetailSerializer(source='user', read_only=True)
    created_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%SZ", read_only=True)
    updated_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%SZ", read_only=True)

    class Meta:
        model = Offer
        fields = [
            'id', 'user', 'title', 'image', 'description', 'created_at', 
            'updated_at', 'details', 'min_price', 'min_delivery_time', 'user_details'
        ]

class OfferDetailCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating OfferDetails nested within an Offer."""
    class Meta:
        model = OfferDetail
        fields = ['price', 'delivery_time_days']

class OfferCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer fpr creating and updating Offer instances with nested details"""
    details = OfferDetailCreateSerializer(many=True)
    
    class Meta:
        model = Offer
        fields = ['title', 'description', 'image', 'details']
    
    def validate_details(self, value):
        """
        Validates that exactly 3 detail packages are provided.
        """
        if len(value) != 3:
            raise serializers.ValidationError(
                f"Exactly 3 detail packages are required, but {len(value)} were provided."
            )
        return value
    
    def create(self, validated_data):
        """
        Handles the creation of an Offer and its nested OfferDetails
        """
        details_data = validated_data.pop('details')
        offer = Offer.objects.create(**validated_data)
        for detail_item in details_data:
            OfferDetail.objects.create(offer=offer, ** detail_item)
        
        return offer

    def update(self, instance, validated_data):
        """
        Handles updating an Offer and its nested details.
        Note: This implementation replaces all old details with the new ones.
        """
        details_data = validated_data.pop('details', None)
        instance.title = validated_data.get('title', instance.title)
        instance.description = validated_data.get('description', instance.description)
        instance.image = validated_data.get('image', instance.image)
        instance.save()
        
        if details_data is not None:
            instance.details.all().delete()
            for detail_data in details_data:
                OfferDetail.objects.create(offer=instance, **detail_data)
            
        return instance
        
class OfferDetailUrlSerializer(serializers.HyperlinkedModelSerializer):
    """Serializer to represent OfferDetails just by their URL."""
    url = serializers.HyperlinkedIdentityField(
        view_name='offerdetail-detail')  # Braucht einen ViewSet für OfferDetail

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
            'details',  # The list of detail URLs
            'min_price',
            'min_delivery_time',
            'user_details',  # The nested user object
        ]
