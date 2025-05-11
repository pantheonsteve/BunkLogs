from dj_rest_auth.serializers import UserDetailsSerializer
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomUserDetailsSerializer(UserDetailsSerializer):
    class Meta(UserDetailsSerializer.Meta):
        model = User
        fields = UserDetailsSerializer.Meta.fields + (
            'is_staff', 'is_superuser', 'date_joined', 'role',
            'first_name', 'last_name', 'username', 'last_login',
        )
        read_only_fields = UserDetailsSerializer.Meta.read_only_fields + (
            'is_staff', 'is_superuser', 'date_joined', 'role', 'last_login',
        )
