from django.contrib import admin
from .models import Offer, OfferDetail

# Register your models here.
class OfferAdmin(admin.ModelAdmin):
    list_display = ('title', 'user')
    
admin.site.register(Offer, OfferAdmin)
admin.site.register(OfferDetail)
