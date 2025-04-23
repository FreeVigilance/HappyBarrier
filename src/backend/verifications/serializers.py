from rest_framework import serializers

from core.constants import PHONE_MAX_LENGTH
from core.validators import PhoneNumberValidator
from verifications.constants import VERIFICATION_CODE_MAX_LENGTH, VERIFICATION_TOKEN_MAX_LENGTH
from verifications.models import Verification
from verifications.validators import VerificationCodeValidator, VerificationTokenValidator


class SendVerificationCodeSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=PHONE_MAX_LENGTH, validators=[PhoneNumberValidator()])
    mode = serializers.ChoiceField(choices=Verification.Mode.choices)


class VerifyCodeSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=PHONE_MAX_LENGTH, validators=[PhoneNumberValidator()])
    code = serializers.CharField(max_length=VERIFICATION_CODE_MAX_LENGTH, validators=[VerificationCodeValidator()])
    verification_token = serializers.CharField(
        max_length=VERIFICATION_TOKEN_MAX_LENGTH, validators=[VerificationTokenValidator()]
    )
