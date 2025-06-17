from rest_framework import generics, permissions
from coderr_app.models import Profile
from .serializers import ProfileSerializer

class ProfileDetailView(generics.RetrieveUpdateAPIView):
    queryset = Profile.objects.select_related('user').all()
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'user__pk' 
    lookup_url_kwarg = 'pk'