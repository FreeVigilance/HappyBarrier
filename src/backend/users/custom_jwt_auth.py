from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken
from rest_framework_simplejwt.settings import api_settings


class CustomJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that enforces user activation status.

    - If the token is invalid, it raises `InvalidToken` (401 Unauthorized).
    - If the user is not found, it raises `AuthenticationFailed` (401 Unauthorized).
    - If the user is inactive (`is_active=False`), it raises `PermissionDenied` (403 Forbidden).
    """

    def get_user(self, validated_token):
        try:
            user_id = validated_token[api_settings.USER_ID_CLAIM]
        except KeyError:
            raise InvalidToken("Token contained no recognizable user identification")

        try:
            user = self.user_model.objects.get(**{api_settings.USER_ID_FIELD: user_id})
        except self.user_model.DoesNotExist:
            raise AuthenticationFailed("User not found.", code="user_not_found")

        if not user.is_active:
            raise PermissionDenied(f"User is blocked. Reason: '{user.block_reason}'.", code="user_inactive")

        return user
