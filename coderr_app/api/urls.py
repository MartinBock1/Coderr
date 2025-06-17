from django.urls import path
from .views import ProfileDetailView

urlpatterns = [
    # Der Name 'pk' im Pfad muss mit `lookup_url_kwarg` in der View übereinstimmen.
    path('profile/<int:pk>/', ProfileDetailView.as_view(), name='profile-detail'),
]