import logging

from rest_framework.decorators import permission_classes
from rest_framework.exceptions import MethodNotAllowed, PermissionDenied
from rest_framework.generics import RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAdminUser
from rest_framework.views import APIView

from action_history.models import BarrierActionLog
from barriers.models import Barrier, UserBarrier
from core.utils import deleted_response, success_response
from phones.models import BarrierPhone
from users.models import User
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
        serializer.is_valid(raise_exception=True)

        serializer.save()
        return success_response(UserSerializer(user).data)

    def delete(self, request, *args, **kwargs):
        """Deactivate account (verification required)"""

        serializer = DeleteUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = self.get_object()
        verification_token = request.data.get("verification_token")

        if user.role == User.Role.SUPERUSER:
            raise PermissionDenied("Superuser account cannot be deleted.")

        verification, error = VerificationService.get_verified_verification_or_error(
            user.phone, verification_token, Verification.Mode.DELETE_ACCOUNT
        )
        if error:
            return error

        user.is_active = False
        user.save(update_fields=["is_active"])

        verification.status = Verification.Status.USED
        verification.save(update_fields=["status"])

        logger.info(f"Deleting user barrier relations on '{user.id}' while deleting user")
        UserBarrier.objects.filter(user=user, is_active=True).update(is_active=False)

        phones = BarrierPhone.objects.filter(user=user, is_active=True)
        for phone in phones:
            _, log = phone.remove(author=BarrierActionLog.Author.USER, reason=BarrierActionLog.Reason.USER_DELETED)
            phone.send_sms_to_delete(log)
            logger.info(
                f"Deleted phone {phone.phone} for user '{user.id}' from barrier '{phone.barrier.id}' "
                f"while deleting user"
            )

        if user.role == User.Role.ADMIN:
            logger.info(f"Deleting all barriers creating by admin '{user.id}' while deleting user")
            Barrier.objects.filter(owner=user, is_active=True).update(is_active=False)

        return deleted_response()

    def put(self, request, *args, **kwargs):
        raise MethodNotAllowed("PUT")


class ChangePhoneView(APIView):
    """Update user's main phone number (verification required with old and new phones)"""

    @staticmethod
    def update_primary_phones_on_user_change(user, old_phone: str, new_phone: str):
        old_phones = BarrierPhone.objects.filter(
            user=user, phone=old_phone, type=BarrierPhone.PhoneType.PRIMARY, is_active=True
        )

        for old_phone_entry in old_phones:
            barrier = old_phone_entry.barrier

            _, log = old_phone_entry.remove(
                author=BarrierActionLog.Author.SYSTEM, reason=BarrierActionLog.Reason.PRIMARY_PHONE_CHANGE
            )
            old_phone_entry.send_sms_to_delete(log)

            new_phone_entry, log = BarrierPhone.create(
                user=user,
                barrier=barrier,
                phone=new_phone,
                type=BarrierPhone.PhoneType.PRIMARY,
                name=user.get_full_name(),
                author=BarrierActionLog.Author.SYSTEM,
                reason=BarrierActionLog.Reason.PRIMARY_PHONE_CHANGE,
            )
            new_phone_entry.send_sms_to_create(log)

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

        user.phone = new_phone
        user.save(update_fields=["phone"])

        verification_old.status = Verification.Status.USED
        verification_old.save(update_fields=["status"])
        verification_new.status = Verification.Status.USED
        verification_new.save(update_fields=["status"])

        self.update_primary_phones_on_user_change(user, old_phone, new_phone)

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
