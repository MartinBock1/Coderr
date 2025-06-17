from rest_framework import generics, permissions

from coderr_app.models import Profile
from .serializers import ProfileSerializer
from .permissions import IsOwnerOrReadOnly 

class ProfileDetailView(generics.RetrieveUpdateAPIView):
    queryset = Profile.objects.select_related('user').all()
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    lookup_field = 'user__pk' 
    lookup_url_kwarg = 'pk'
