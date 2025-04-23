import logging

from rest_framework import status
from rest_framework.decorators import permission_classes
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.generics import RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAdminUser
from rest_framework.views import APIView

from core.utils import deleted_response, error_response, success_response
from users.serializers import (
    ChangePasswordSerializer,
    ChangePhoneSerializer,
    DeleteUserSerializer,
    UpdateUserSerializer,
    UserSerializer,
)
from verifications.models import Verification, VerificationService

logger = logging.getLogger(__name__)


class UserAccountView(RetrieveUpdateDestroyAPIView):
    """Retrieve, update, and delete the user profile"""

    serializer_class = UserSerializer

    def get_object(self):
        """Retrieve the current user's profile"""

        return self.request.user

    def patch(self, request, *args, **kwargs):
        """Edit profile (full_name, phone privacy)"""

        user = self.get_object()
        serializer = UpdateUserSerializer(self.get_object(), data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return success_response(UserSerializer(user).data)

        return error_response(serializer.errors, status.HTTP_400_BAD_REQUEST)

    def delete(self, request, *args, **kwargs):
        """Deactivate account (verification required)"""

        serializer = DeleteUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = self.get_object()
        verification_token = request.data.get("verification_token")

        verification, error = VerificationService.get_verified_verification_or_error(
            user.phone, verification_token, Verification.Mode.DELETE_ACCOUNT
        )
        if error:
            return error

        user.is_active = False
        user.save(update_fields=["is_active"])

        verification.status = Verification.Status.USED
        verification.save(update_fields=["status"])

        return deleted_response()

    def put(self, request, *args, **kwargs):
        raise MethodNotAllowed("PUT")


class ChangePhoneView(APIView):
    """Update user's main phone number (verification required with old and new phones)"""

    def patch(self, request):
        serializer = ChangePhoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        old_phone = user.phone
        new_phone = serializer.validated_data["new_phone"]
        old_verification_token = serializer.validated_data["old_verification_token"]
        new_verification_token = serializer.validated_data["new_verification_token"]

        verification_old, error = VerificationService.get_verified_verification_or_error(
            old_phone, old_verification_token, Verification.Mode.CHANGE_PHONE_OLD
        )
        if error:
            return error

        verification_new, error = VerificationService.get_verified_verification_or_error(
            new_phone, new_verification_token, Verification.Mode.CHANGE_PHONE_NEW
        )
        if error:
            return error

        # TODO - add changing phone with other tables like barrier
        user.phone = new_phone
        user.save(update_fields=["phone"])

        verification_old.status = Verification.Status.USED
        verification_old.save(update_fields=["status"])
        verification_new.status = Verification.Status.USED
        verification_new.save(update_fields=["status"])

        return success_response(UserSerializer(user).data)


@permission_classes([IsAdminUser])
class ChangePasswordView(APIView):
    """Update admin password (verification required)"""

    def patch(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        phone = user.phone
        new_password = serializer.validated_data["new_password"]
        verification_token = serializer.validated_data["verification_token"]

        verification, error = VerificationService.get_verified_verification_or_error(
            phone, verification_token, Verification.Mode.CHANGE_PASSWORD
        )
        if error:
            return error

        user.set_password(new_password)
        user.save()

        verification.status = Verification.Status.USED
        verification.save(update_fields=["status"])

        return success_response(UserSerializer(user).data)
