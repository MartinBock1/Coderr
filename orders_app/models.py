from django.db import models
from django.conf import settings
from django.db.models import JSONField

# Create your models here.
class Order(models.Model):
    customer_user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='customer_orders', on_delete=models.CASCADE)
    business_user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='business_orders', on_delete=models.CASCADE)
    
    title = models.CharField(max_length=255)
    status = models.CharField(max_length=50, default='in_progress')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    revisions = models.IntegerField(default=3) 
    delivery_time_in_days = models.IntegerField(default=5)
    features =  JSONField(default=list)
    
    offer_type = models.CharField(max_length=50, default='basic')
    status = models.CharField(max_length=50, default='in_progress')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Order {self.id}: {self.title}"
    