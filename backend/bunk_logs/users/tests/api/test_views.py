import pytest
from rest_framework.test import APIRequestFactory

from bunk_logs.users.api.views import UserViewSet
from bunk_logs.users.models import User


class TestUserViewSet:
    @pytest.fixture
    def api_rf(self) -> APIRequestFactory:
        return APIRequestFactory()

    def test_get_queryset(self, user: User, api_rf: APIRequestFactory):
        view = UserViewSet()
        request = api_rf.get("/fake-url/")
        request.user = user

        view.request = request

        assert user in view.get_queryset()

    def test_me(self, user: User, api_rf: APIRequestFactory):
        view = UserViewSet()
        request = api_rf.get("/fake-url/")
        request.user = user

        view.request = request
        view.format_kwarg = None

        response = view.me(request)  # type: ignore[call-arg, arg-type, misc]

        assert response.data["email"] == user.email
        assert response.data["first_name"] == user.first_name
        assert response.data["last_name"] == user.last_name
