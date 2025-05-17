import logging

from django.utils.timezone import now
from rest_framework import status
from rest_framework.decorators import authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from core.utils import created_response, error_response, success_response
from message_management.services import SMSService
from users.models import User
from verifications.constants import VERIFICATION_CODE_RESEND_DELAY
from verifications.models import Verification, VerificationService
from verifications.serializers import SendVerificationCodeSerializer, VerifyCodeSerializer
from verifications.utils import apply_checks

logger = logging.getLogger(__name__)


@authentication_classes([])
@permission_classes([AllowAny])
class SendVerificationCodeView(APIView):
    """Send a verification code to the user's phone."""

    def post(self, request):
        VerificationService.clean()

        serializer = SendVerificationCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data["phone"]
        mode = serializer.validated_data["mode"]

        # Check if user can send new code.
        if it := apply_checks(
            lambda: User.objects.check_phone_blocked(phone),
            lambda: VerificationService.check_fail_limits(phone),
            lambda: VerificationService.check_unverified_limits(phone),
            lambda: VerificationService.check_verification_mode(phone, mode),
        ):
            return it

        # Check if a code was sent within the last minutes
        recent_verification = Verification.get_recent_verification(phone)
        if recent_verification:
            resend_delay = VERIFICATION_CODE_RESEND_DELAY - (now() - recent_verification.created_at).seconds
            return error_response(
                "Verification code was already sent. Try again later.",
                status.HTTP_429_TOO_MANY_REQUESTS,
                retry_after=resend_delay,
                headers={"Retry-After": str(resend_delay)},
            )

        verification = VerificationService.create_new_verification(phone, mode)

        SMSService.send_verification(verification)

        return created_response(
            {
                "message": "Verification code sent.",
                "verification_token": verification.verification_token,
                "code": verification.code,
            }
        )


@authentication_classes([])
@permission_classes([AllowAny])
class VerifyCodeView(APIView):
    """Verify the code sent to the user's phone using a verification token."""

    def patch(self, request):
        VerificationService.clean()

        serializer = VerifyCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data["phone"]
        code = serializer.validated_data["code"]
        verification_token = serializer.validated_data["verification_token"]

        # Check if user with this phone is blocked or not.
        # Count all failed attempts for the last 30 minutes and return 429 if exceeded
        if it := apply_checks(
            lambda: User.objects.check_phone_blocked(phone),
            lambda: VerificationService.check_fail_limits(phone),
            lambda: VerificationService.validate_verification_is_usable(phone, verification_token),
        ):
            return it

        verification = Verification.get_verification_by_token(verification_token)

        if verification.code != code:
            verification.failed_attempts += 1
            verification.save()
            return error_response("Invalid code.", status.HTTP_400_BAD_REQUEST)

        verification.status = Verification.Status.VERIFIED
        verification.save()

        return success_response({"message": "Code verified successfully."}, status.HTTP_200_OK)
