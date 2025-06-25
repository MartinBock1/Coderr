from django.db.models import Q
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from ..models import Order
from .serializers import OrderSerializer


class OrderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer
    
    def get_queryset(self):
        user = self.request.user
        return Order.objects.filter(
            Q(customer_user=user) | Q (business_user=user)
        )