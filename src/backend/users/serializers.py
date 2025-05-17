from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from core.constants import PHONE_MAX_LENGTH
from core.validators import PhoneNumberValidator
from users.models import User
from verifications.constants import VERIFICATION_TOKEN_MAX_LENGTH
from verifications.validators import VerificationTokenValidator


class AdminPasswordVerificationSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=PHONE_MAX_LENGTH, validators=[PhoneNumberValidator()])
    password = serializers.CharField()


class LoginSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=PHONE_MAX_LENGTH, validators=[PhoneNumberValidator()])
    verification_token = serializers.CharField(
        max_length=VERIFICATION_TOKEN_MAX_LENGTH, validators=[VerificationTokenValidator()]
    )


class CheckAdminSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=PHONE_MAX_LENGTH, validators=[PhoneNumberValidator()])


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "phone", "full_name", "role", "phone_privacy", "is_active"]


class UpdateUserSerializer(serializers.ModelSerializer):
    phone_privacy = serializers.ChoiceField(
        choices=User.PhonePrivacy.choices,
        error_messages={"invalid_choice": f"Invalid phone privacy. Valid options are: {User.PhonePrivacy.values}"},
        required=False,
    )

    class Meta:
        model = User
        fields = ["full_name", "phone_privacy"]


class DeleteUserSerializer(serializers.Serializer):
    verification_token = serializers.CharField(
        max_length=VERIFICATION_TOKEN_MAX_LENGTH, validators=[VerificationTokenValidator()]
    )


class ChangePhoneSerializer(serializers.Serializer):
    new_phone = serializers.CharField(max_length=PHONE_MAX_LENGTH, validators=[PhoneNumberValidator()])
    old_verification_token = serializers.CharField(
        max_length=VERIFICATION_TOKEN_MAX_LENGTH, validators=[VerificationTokenValidator()]
    )
    new_verification_token = serializers.CharField(
        max_length=VERIFICATION_TOKEN_MAX_LENGTH, validators=[VerificationTokenValidator()]
    )

    @staticmethod
    def validate_new_phone(value):
        """Check if new phone number is already in use."""

        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("Given new phone number is already in use.")
        return value


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    verification_token = serializers.CharField(
        max_length=VERIFICATION_TOKEN_MAX_LENGTH, validators=[VerificationTokenValidator()]
    )

    def validate_old_password(self, value):
        """Check if old password is correct."""

        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value


class ResetPasswordSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=PHONE_MAX_LENGTH, validators=[PhoneNumberValidator()])
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    verification_token = serializers.CharField(
        max_length=VERIFICATION_TOKEN_MAX_LENGTH, validators=[VerificationTokenValidator()]
    )


class SearchUserSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=PHONE_MAX_LENGTH, validators=[PhoneNumberValidator()])
