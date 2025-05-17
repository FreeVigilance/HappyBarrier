import pytest
from django.http import HttpRequest
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken
from rest_framework_simplejwt.settings import api_settings

from users.custom_jwt_auth import CustomJWTAuthentication


@pytest.mark.django_db
class TestCustomJWTAuthentication:
    def setup_method(self):
        self.auth = CustomJWTAuthentication()

    def test_returns_user_if_valid_and_active(self, admin_user):
        token = {api_settings.USER_ID_CLAIM: getattr(admin_user, api_settings.USER_ID_FIELD)}
        user = self.auth.get_user(token)

        assert user == admin_user

    def test_raises_invalid_token_if_missing_claim(self):
        token = {}

        with pytest.raises(InvalidToken) as exc_info:
            self.auth.get_user(token)

        assert "Token contained no recognizable user identification" in str(exc_info.value)

    def test_raises_invalid_token_on_invalid_jwt(self):
        auth = CustomJWTAuthentication()

        http_request = HttpRequest()
        http_request.META["HTTP_AUTHORIZATION"] = "Bearer invalid.token"
        drf_request = Request(http_request)

        with pytest.raises(InvalidToken) as exc_info:
            auth.authenticate(drf_request)

        error = exc_info.value
        assert error.detail["code"] == "token_not_valid"
        assert error.detail["detail"] == "Given token not valid for any token type"

        messages = error.detail["messages"]
        assert any("Token is invalid or expired" in msg["message"] for msg in messages)

    def test_raises_authentication_failed_if_user_not_found(self):
        token = {api_settings.USER_ID_CLAIM: 999999}

        with pytest.raises(AuthenticationFailed) as exc_info:
            self.auth.get_user(token)

        assert exc_info.value.detail["detail"] == "User not found."
        assert exc_info.value.detail["code"] == "user_not_found"

    def test_raises_permission_denied_if_user_inactive(self, admin_user):
        admin_user.is_active = False
        admin_user.block_reason = "Spamming"
        admin_user.save()

        token = {api_settings.USER_ID_CLAIM: getattr(admin_user, api_settings.USER_ID_FIELD)}

        with pytest.raises(PermissionDenied) as exc_info:
            self.auth.get_user(token)

        assert str(exc_info.value) == "User is blocked. Reason: 'Spamming'."
