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
    delivery_time_in_days = serializers.IntegerField(source='delivery_time_days')

    class Meta:
        model = OfferDetail
        fields = [
            'id',
            'title',
            'revisions',
            'delivery_time_in_days',
            'price',
            'features',
            'offer_type',
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
    """
    Serializer for creating AND updating OfferDetails.
    The 'id' is made read-only for creation but is used for matching during updates.
    """
    delivery_time_in_days = serializers.IntegerField(source='delivery_time_days')

    class Meta:
        model = OfferDetail
        fields = [
            'title',
            'price',
            'delivery_time_in_days',
            'description',
            'image',
            'revisions',
            'features',
            'offer_type'
        ]


class OfferCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer fpr creating and updating Offer instances with nested details"""
    details = OfferDetailCreateSerializer(many=True)

    class Meta:
        model = Offer
        fields = ['title', 'description', 'image', 'details']

    def validate_details(self, value):
        """
        Validates that exactly 3 detail packages are provided during CREATION.
        This validation is skipped during an update (PATCH/PUT).
        """
        # self.instance is None during creation (POST).
        # self.instance is not None during an update (PATCH/PUT).
        if self.instance is None:
            # This is a create operation, so enforce the rule.
            if len(value) != 3:
                raise serializers.ValidationError(
                    f"Exactly 3 detail packages are required for creation, but {len(value)} were provided."
                )
        
        # For update operations, we don't validate the count, as it's a partial update.
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
        Handles partial updates for an Offer and its nested details.
        It updates details in-place based on their provided 'offer_type'.
        """
        instance.title = validated_data.get('title', instance.title)
        instance.description = validated_data.get('description', instance.description)
        instance.image = validated_data.get('image', instance.image)
        instance.save()

        # Handle nested details for partial update using 'offer_type'
        details_data = validated_data.get('details')
        if details_data:
           # Create a dictionary of existing details keyed by 'offer_type' for quick lookups
            existing_details = {detail.offer_type: detail for detail in instance.details.all()}

            for detail_data in details_data:
                offer_type = detail_data.get('offer_type')
                if not offer_type:
                    raise serializers.ValidationError(
                        {"details": "Each detail to be updated must have an 'offer_type'."}
                    )

                detail_instance = existing_details.get(str(offer_type))
                if not detail_instance:
                    raise serializers.ValidationError(
                        {"details":
                            f"A detail with offer_type '{offer_type}' does not exist for this offer."
                         }
                    )

                # Update the specific detail instance
                # Wir verwenden einen Serializer für die Aktualisierung, um die Logik wiederzuverwenden
                # 'partial=True' ist entscheidend, damit nur die übergebenen Felder aktualisiert werden.
                detail_serializer = OfferDetailCreateSerializer(
                    instance=detail_instance,
                    data=detail_data,
                    partial=True
                )
                detail_serializer.is_valid(raise_exception=True)
                detail_serializer.save()

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


class OfferRetrieveSerializer(serializers.ModelSerializer):
    """
    Serializer for retrieving a single Offer instance.
    Does not include the nested 'user_details' object, as per API spec.
    """
    # Calculated fields
    min_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    min_delivery_time = serializers.IntegerField(read_only=True, source='min_delivery_time_days')

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
            # 'user_details' is intentionally omitted here.
        ]
