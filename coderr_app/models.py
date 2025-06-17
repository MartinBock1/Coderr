from django.db import models
from django.contrib.auth.models import User

# Create your models here.

def user_directory_path(instance, filename):
    return f'profiles/{instance.user.id}/{filename}'


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    class UserType(models.TextChoices):
        CUSTOMER = 'customer', 'Kunde'
        BUSINESS = 'business', 'Geschäft'

    file = models.ImageField(upload_to=user_directory_path, null=True, blank=True, verbose_name="Profilbild")
    location = models.CharField(max_length=100, blank=True, default='', verbose_name="Standort")
    tel = models.CharField(max_length=20, blank=True, default='', verbose_name="Telefonnummer")
    description = models.TextField(blank=True, default='', verbose_name="Beschreibung")
    working_hours = models.CharField(max_length=50, blank=True, default='', verbose_name="Öffnungszeiten")
    type = models.CharField(max_length=10, choices=UserType.choices, default=UserType.CUSTOMER, verbose_name="Benutzertyp")    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profil von {self.user.username}"
    
    @property
    def file_url(self):
        if self.file and hasattr(self.file, 'url'):
            return self.file.url
        return None