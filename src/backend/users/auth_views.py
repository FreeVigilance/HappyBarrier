import logging

from django.contrib.auth import authenticate
from django.utils.timezone import now
from rest_framework import status
from rest_framework.decorators import authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from core.utils import error_response, success_response
from users.models import User
from users.serializers import (
    AdminPasswordVerificationSerializer,
    CheckAdminSerializer,
    LoginSerializer,
    ResetPasswordSerializer,
)
from verifications.models import Verification, VerificationService

logger = logging.getLogger(__name__)


@authentication_classes([])
@permission_classes([AllowAny])
class AdminPasswordVerificationView(APIView):
    """Verify the administrator's password."""

    def post(self, request):
        serializer = AdminPasswordVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data["phone"]
        password = serializer.validated_data["password"]

        user = User.objects.get_by_phone(phone)

        if user is None:
            return error_response("User not found.", status.HTTP_404_NOT_FOUND)
        if not user.is_active:
            return error_response(f"User is blocked. Reason: '{user.block_reason}'.", status.HTTP_403_FORBIDDEN)
        if user.role == User.Role.USER:
            return error_response("You do not have permission to perform this action.", status.HTTP_403_FORBIDDEN)
        if not authenticate(username=phone, password=password):
            return error_response("Invalid phone or password.", status.HTTP_403_FORBIDDEN)

        return success_response({"message": "Password verified successfully."})


@authentication_classes([])
@permission_classes([AllowAny])
class LoginView(APIView):
    """Login using phone and verification token."""

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data["phone"]
        verification_token = serializer.validated_data["verification_token"]

        # Find the verification entry
        verification, error = VerificationService.get_verified_verification_or_error(
            phone, verification_token, Verification.Mode.LOGIN
        )
        if error:
            return error

        # Check if user exists, otherwise create a new one
        user, created = User.objects.get_or_create(phone=phone, defaults={"is_active": True})

        if not user.is_active:
            reason = user.block_reason
            return error_response(f"User is blocked. Reason: '{reason}'.", status.HTTP_403_FORBIDDEN)

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        verification.status = Verification.Status.USED
        verification.save(update_fields=["status"])
        user.last_login = now()
        user.save(update_fields=["last_login"])

        return success_response(
            {
                "access_token": access_token,
                "refresh_token": str(refresh),
            }
        )


@authentication_classes([])
@permission_classes([AllowAny])
class CheckAdminView(APIView):
    """Check, if user with given phone number is admin or not."""

    def post(self, request):
        serializer = CheckAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data["phone"]

        user = User.objects.get_by_phone(phone)

        if not user or not user.is_active:
            return success_response({"is_admin": False})

        return success_response({"is_admin": user.role != User.Role.USER})


@authentication_classes([])
@permission_classes([AllowAny])
class ResetPasswordView(APIView):
    """Reset admin password (verification required)"""

    def patch(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.get_by_phone(serializer.validated_data["phone"])
        if not user:
            return error_response("User not found.", status.HTTP_404_NOT_FOUND)
        if not user.is_active:
            return error_response(f"User is blocked. Reason: '{user.block_reason}'.", status.HTTP_403_FORBIDDEN)
        if user.role == User.Role.USER:
            return error_response("You do not have permission to perform this action.", status.HTTP_403_FORBIDDEN)

        phone = user.phone
        new_password = serializer.validated_data["new_password"]
        verification_token = serializer.validated_data["verification_token"]

        verification, error = VerificationService.get_verified_verification_or_error(
            phone, verification_token, Verification.Mode.RESET_PASSWORD
        )
        if error:
            return error

        user.set_password(new_password)
        user.save()

        verification.status = Verification.Status.USED
        verification.save(update_fields=["status"])

        return success_response({"message": "Password successfully reset."})
