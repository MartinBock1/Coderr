from rest_framework import viewsets, permissions

from offers_app.models import Offers
from .permissions import IsOwnerOrReadOnly
from .serializers import (
    OffersSerializer,
)

class OffersViewSet(viewsets.ModelViewSet):
    queryset = Offers.objects.all()
    serializer_class = OffersSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)  # Assuming the Offers model has an 'owner' field
