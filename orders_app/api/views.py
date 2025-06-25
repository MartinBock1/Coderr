from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from ..models import Order
from .serializers import OrderSerializer, CreateOrderSerializer, OrderStatusUpdateSerializer
from .permissions import IsBusinessUserAndOwner
from offers_app.models import OfferDetail


class OrderViewSet(viewsets.ModelViewSet):
    pagination_class = None
    
    def get_permissions(self):
        if self.action == 'destroy':
            self.permission_classes = [IsAdminUser]
        elif self.action in ['update', 'partial_update']:
            self.permission_classes = [IsAuthenticated, IsBusinessUserAndOwner]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()
    
    def get_queryset(self):
        user = self.request.user
        return Order.objects.filter(
            Q(customer_user=user) | Q (business_user=user)
        )

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return OrderStatusUpdateSerializer
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
    
    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        self.perform_update(serializer)
        
        output_serializer = OrderSerializer(instance)
        
        return Response(output_serializer.data)