from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ..models import Order
from .serializers import OrderSerializer, CreateOrderSerializer
from offers_app.models import OfferDetail


class OrderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = None
    
    def get_queryset(self):
        user = self.request.user
        return Order.objects.filter(
            Q(customer_user=user) | Q (business_user=user)
        )
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateOrderSerializer
        return OrderSerializer
    
    def create(self, request, *args, **kwargs):
        input_serializer = self.get_serializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        offer_detail_id = input_serializer.validated_data['offer_detail_id']

        try:
            offer_detail = OfferDetail.objects.select_related('offer__user').get(pk=offer_detail_id)
        except OfferDetail.DoesNotExist:
            return Response({"detail": "Offer detail not found."}, status=status.HTTP_404_NOT_FOUND)
        
        business_user = offer_detail.offer.user
        if business_user == request.user:
            return Response(
                {"detail": "You cannot create an order for your own offer."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        order = Order.objects.create(
            customer_user=request.user,
            business_user=business_user,
            title=offer_detail.title,
            price=offer_detail.price,
            revisions=offer_detail.revisions,
            delivery_time_in_days=offer_detail.delivery_time_in_days,
            features=offer_detail.features,
            offer_type=offer_detail.offer_type
        )

        output_serializer = OrderSerializer(order)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)