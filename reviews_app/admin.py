from django.contrib import admin
from .models import Review

class ReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'business_user', 'reviewer', 'rating', 'description', 'created_at')
    

# Register your models here.
admin.site.register(Review, ReviewAdmin)