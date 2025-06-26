from django.contrib import admin
from .models import Order

class OrderAdmin(admin.ModelAdmin):
    list_display = ('title', 'offer_type', 'price', 'status', 'created_at')
    

# Register your models here.
admin.site.register(Order, OrderAdmin)
