import logging
import random
import string
from datetime import timedelta

from django.db import models
from django.utils.timezone import now
from rest_framework import status

from core.constants import CHOICE_MAX_LENGTH, PHONE_MAX_LENGTH
from core.utils import error_response
from core.validators import PhoneNumberValidator
from verifications.constants import (
    DELETION_DAYS,
    EXPIRATION_MINUTES,
    VERIFICATION_CODE_MAX_LENGTH,
    VERIFICATION_CODE_RESEND_DELAY,
    VERIFICATION_TOKEN_MAX_LENGTH,
)
from verifications.validators import VerificationCodeValidator, VerificationTokenValidator

logger = logging.getLogger(__name__)

MAX_FAIL_COUNT = 5


class VerificationService:
    """Service class for handling verification-related queries."""

    @staticmethod
    def generate_verification_code():
        """Generates a random 6-digit verification code."""

        return "".join(random.choices(string.digits, k=VERIFICATION_CODE_MAX_LENGTH))

    @staticmethod
    def generate_verification_token():
        """Generates a random alphanumeric verification token."""

        return "".join(random.choices(string.ascii_letters + string.digits, k=VERIFICATION_TOKEN_MAX_LENGTH))

    @staticmethod
    def create_new_verification(phone, mode):
        """Creates a new verification entry with a random verification token."""

        return Verification.objects.create(
            phone=phone,
            code=VerificationService.generate_verification_code(),
            verification_token=VerificationService.generate_verification_token(),
            mode=mode,
            status=Verification.Status.SENT,
        )

    @staticmethod
    def clean():
        """Deletes outdated verification codes and marks old sent codes as expired."""

        now_time = now()
        expiration_time = now_time - timedelta(minutes=EXPIRATION_MINUTES)
        deletion_time = now_time - timedelta(days=DELETION_DAYS)

        Verification.objects.filter(created_at__lte=deletion_time).delete()
        Verification.objects.filter(
            status__in=[Verification.Status.SENT, Verification.Status.VERIFIED],
            created_at__lte=expiration_time,
        ).update(status=Verification.Status.EXPIRED)

    @staticmethod
    def check_fail_limits(phone):
        """
        Counts total failed verification attempts for the last minutes (before expiration).
        Checks if it exceeds the limit.
        """

        count = (
            Verification.objects.filter(
                phone=phone,
                created_at__gte=now() - timedelta(minutes=EXPIRATION_MINUTES),
                failed_attempts__gt=0,
            ).aggregate(total_attempts=models.Sum(models.F("failed_attempts"), default=0))["total_attempts"]
            or 0
        )

        if count >= MAX_FAIL_COUNT:
            return error_response("Too many verification attempts. Try again later.", status.HTTP_429_TOO_MANY_REQUESTS)

    @staticmethod
    def check_unverified_limits(phone):
        """Counts the number of unverified codes for a given phone number and checks if it exceeds the limit."""

        if Verification.objects.filter(phone=phone, status=Verification.Status.SENT).count() >= MAX_FAIL_COUNT:
            return error_response("Too many unverified codes. Try again later.", status.HTTP_429_TOO_MANY_REQUESTS)

    @staticmethod
    def _check_verification_object(verification, phone):
        if not verification:
            return error_response("Verification not found.", status.HTTP_404_NOT_FOUND)
        if verification.phone != phone:
            return error_response("Phone number does not match the verification record.", status.HTTP_400_BAD_REQUEST)

    @staticmethod
    def validate_verification_is_usable(phone, token):
        verification = Verification.objects.filter(verification_token=token).first()

        if error := VerificationService._check_verification_object(verification, phone):
            return error

        if verification.status in [Verification.Status.VERIFIED, Verification.Status.USED]:
            return error_response(
                "This code has already been used. Please request a new one.", status.HTTP_409_CONFLICT
            )

        if verification.status == Verification.Status.EXPIRED:
            return error_response("This code has expired. Please request a new one.", status.HTTP_410_GONE)

    @staticmethod
    def get_verified_verification_or_error(phone, token, mode):
        """Validates the verification token for given mode."""

        verification = Verification.objects.filter(verification_token=token).first()

        if error := VerificationService._check_verification_object(verification, phone):
            return None, error

        if verification.mode != mode:
            return None, error_response("Invalid verification mode.", status.HTTP_404_NOT_FOUND)

        if verification.status != Verification.Status.VERIFIED:
            return None, error_response("Phone number has not been verified.", status.HTTP_400_BAD_REQUEST)

        return verification, None


class Verification(models.Model):
    """Verification codes sent via SMS for user authentication and account-related actions."""

    class Meta:
        db_table = "verification"

    class Mode(models.TextChoices):
        LOGIN = "login", "Login"
        CHANGE_PHONE_OLD = "change_phone_old", "Change Old Phone"
        CHANGE_PHONE_NEW = "change_phone_new", "Change New Phone"
        RESET_PASSWORD = "reset_password", "Reset Password"
        CHANGE_PASSWORD = "change_password", "Change Password"
        DELETE_ACCOUNT = "delete_account", "Delete Account"

    class Status(models.TextChoices):
        SENT = "sent", "Sent"
        VERIFIED = "verified", "Verified"
        USED = "used", "Used"
        EXPIRED = "expired", "Expired"

    phone = models.CharField(
        max_length=PHONE_MAX_LENGTH,
        db_index=True,
        validators=[PhoneNumberValidator()],
        help_text="Enter a phone number in the format +7XXXXXXXXXX.",
    )
    code = models.CharField(max_length=VERIFICATION_CODE_MAX_LENGTH, validators=[VerificationCodeValidator()])
    verification_token = models.CharField(
        max_length=VERIFICATION_TOKEN_MAX_LENGTH,
        unique=True,
        validators=[VerificationTokenValidator()],
        help_text="Unique token for verifying the code.",
    )
    mode = models.CharField(max_length=CHOICE_MAX_LENGTH, choices=Mode.choices)
    status = models.CharField(max_length=CHOICE_MAX_LENGTH, choices=Status.choices, default=Status.SENT)
    failed_attempts = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.phone} - {self.mode} - {self.status} - {self.verification_token}"

    @classmethod
    def get_verification_by_token(cls, token):
        """Fetches the verification entry by its verification token."""

        return cls.objects.filter(verification_token=token).first()

    @classmethod
    def get_recent_verification(cls, phone):
        """Returns the most recent verification code within the resend delay window."""

        return (
            cls.objects.filter(
                phone=phone,
                created_at__gte=now() - timedelta(seconds=VERIFICATION_CODE_RESEND_DELAY),
                status=cls.Status.SENT,
            )
            .order_by("-created_at")
            .first()
        )
