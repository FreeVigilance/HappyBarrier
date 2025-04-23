from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken


class CustomJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that enforces user activation status.

    - If the token is invalid, it raises `InvalidToken` (401 Unauthorized).
    - If the user is not found, it raises `AuthenticationFailed` (401 Unauthorized).
    - If the user is inactive (`is_active=False`), it raises `PermissionDenied` (403 Forbidden).
    """

    def get_user(self, validated_token):
        try:
            user = super().get_user(validated_token)
        except InvalidToken as e:
            raise e
        except AuthenticationFailed as e:
            if e.detail == "User not found":
                raise e
            else:
                raise PermissionDenied("User is blocked")

        return user
