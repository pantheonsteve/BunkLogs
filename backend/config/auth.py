from django.contrib.auth import get_user_model
from dj_rest_auth.serializers import JWTSerializer as DefaultJWTSerializer
from rest_framework import serializers

User = get_user_model()

class UserDetailsSerializer(serializers.ModelSerializer):
    """
    User model w/o password
    """
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')
        read_only_fields = ('email',)

class CustomJWTSerializer(DefaultJWTSerializer):
    """
    Custom JWT Serializer
    """
    # No need to define Meta class for CustomJWTSerializer as we're inheriting from DefaultJWTSerializer
    # The error was trying to access DefaultJWTSerializer.Meta.fields which doesn't exist
    pass