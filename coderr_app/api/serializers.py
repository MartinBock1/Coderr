from rest_framework import serializers
from django.contrib.auth.models import User
from coderr_app.models import Profile

class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email')
    first_name = serializers.CharField(source='user.first_name', allow_blank=True)
    last_name = serializers.CharField(source='user.last_name', allow_blank=True)
    file = serializers.CharField(source='file_url', read_only=True)
    user = serializers.IntegerField(source='user.id', read_only=True)

    class Meta:
        model = Profile
        fields = [
            'user',
            'username',
            'first_name',
            'last_name',
            'file',
            'location',
            'tel',
            'description',
            'working_hours',
            'type',
            'email',
            'created_at'
        ]
        read_only_fields = ['created_at']

    # Überschreiben der update-Methode, um sowohl das Profil als auch den User zu aktualisieren.
    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        user = instance.user
        user.email = user_data.get('email', user.email)
        user.first_name = user_data.get('first_name', user.first_name)
        user.last_name = user_data.get('last_name', user.last_name)
        user.save()
        instance = super().update(instance, validated_data)
        return instance