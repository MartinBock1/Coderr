from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Profile

# Register your models here.


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profil'
    fk_name = 'user'


class CustomUserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)

    def get_profile_type(self, instance):
        return instance.profile.type
    get_profile_type.short_description = 'Typ'

    def get_profile_location(self, instance):
        return instance.profile.location
    get_profile_location.short_description = 'Standort'

    list_display = ('username', 'email', 'first_name', 'last_name',
                    'is_staff', 'get_profile_type', 'get_profile_location')

    search_fields = BaseUserAdmin.search_fields + ('profile__location', 'profile__tel')


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
