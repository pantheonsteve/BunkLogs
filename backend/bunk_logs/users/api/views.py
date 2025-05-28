from django.contrib.auth import get_user_model
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from bunk_logs.users.serializers import UserSerializer

User = get_user_model()


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for User model.
    - GET /api/users/ - List all users (staff only)
    - GET /api/users/{id}/ - Retrieve specific user
    - GET /api/users/me/ - Get current user details
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "pk"

    def get_queryset(self):
        """
        Return all users if staff, otherwise return just the current user.
        """
        if self.request.user.is_staff:
            return User.objects.all()
        else:
            return User.objects.filter(pk=self.request.user.pk)

    @action(detail=False, methods=["get"])
    def me(self, request):
        """
        Return current user details.
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
