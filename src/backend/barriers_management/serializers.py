from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from barriers.models import Barrier, BarrierLimit
from barriers.validators import DevicePasswordValidator
from core.utils import ConflictError
from message_management.config_loader import get_phone_command
from message_management.enums import PhoneCommand


class AdminBarrierSerializer(serializers.ModelSerializer):
    """Serializer for viewing a barrier from the admin's perspective"""

    class Meta:
        model = Barrier
        exclude = ("device_password",)


class CreateBarrierSerializer(serializers.ModelSerializer):
    """Serializer for creating a new barrier"""

    additional_info = serializers.CharField(required=True, allow_blank=True)
    device_phones_amount = serializers.IntegerField(required=True)
    device_model = serializers.ChoiceField(
        choices=Barrier.Model.choices,
        error_messages={"invalid_choice": f"Invalid device model. Valid models are: {Barrier.Model.values}"},
    )

    class Meta:
        model = Barrier
        fields = [
            "address",
            "device_phone",
            "device_model",
            "device_phones_amount",
            "device_password",
            "additional_info",
            "is_public",
        ]

    def validate_device_phone(self, value):
        """Check if a device with the given phone number already exists"""

        if Barrier.objects.filter(device_phone=value, is_active=True).exists():
            raise ConflictError("This phone is already taken by another barrier.")
        return value

    def validate_device_phones_amount(self, value):
        """Ensure `device_phones_amount` is greater than 0"""

        if value <= 0:
            raise serializers.ValidationError("The number of device phone slots must be greater than 0.")
        return value

    def validate(self, attrs):
        """Conditional password validation based on device model"""

        model = attrs["device_model"]
        password = attrs.get("device_password")

        if model != Barrier.Model.TELEMETRICA:
            if not password:
                raise serializers.ValidationError(
                    {"device_password": "Device password is required for this device model."}
                )

            try:
                DevicePasswordValidator()(password)
            except DjangoValidationError as e:
                raise serializers.ValidationError({"device_password": list(e.messages)})

        try:
            get_phone_command(model, PhoneCommand.ADD)
            get_phone_command(model, PhoneCommand.DELETE)
        except Exception as e:
            msg = f"Device model '{model}' is not supported: {str(e)}"
            raise serializers.ValidationError({"device_model": msg})

        return attrs

    def create(self, validated_data):
        """Create a barrier and automatically assign the current user as the owner"""

        request = self.context["request"]
        validated_data["owner"] = request.user
        return super().create(validated_data)


class UpdateBarrierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Barrier
        # TODO - how to change password? there need to be stop for sms when password changes!
        fields = ["device_password", "additional_info", "is_public"]

    def validate(self, attrs):
        """Conditional password validation when updating the barrier"""

        model = self.instance.device_model
        password = attrs.get("device_password")

        if model != Barrier.Model.TELEMETRICA:
            if password:
                try:
                    DevicePasswordValidator()(password)
                except DjangoValidationError as e:
                    raise serializers.ValidationError({"device_password": list(e.messages)})

        return attrs


class UpdateBarrierLimitSerializer(serializers.ModelSerializer):
    """Serializer for updating/creating barrier limits"""

    user_phone_limit = serializers.IntegerField(min_value=0, allow_null=True, required=False)
    user_temp_phone_limit = serializers.IntegerField(min_value=0, allow_null=True, required=False)
    global_temp_phone_limit = serializers.IntegerField(min_value=0, allow_null=True, required=False)
    user_schedule_phone_limit = serializers.IntegerField(min_value=0, allow_null=True, required=False)
    global_schedule_phone_limit = serializers.IntegerField(min_value=0, allow_null=True, required=False)
    schedule_interval_limit = serializers.IntegerField(min_value=0, allow_null=True, required=False)
    sms_weekly_limit = serializers.IntegerField(min_value=0, allow_null=True, required=False)

    class Meta:
        model = BarrierLimit
        fields = [
            "user_phone_limit",
            "user_temp_phone_limit",
            "global_temp_phone_limit",
            "user_schedule_phone_limit",
            "global_schedule_phone_limit",
            "schedule_interval_limit",
            "sms_weekly_limit",
        ]

    def validate(self, attrs):
        allowed_fields = set(self.fields.keys())
        received_fields = set(self.initial_data.keys())

        unknown = received_fields - allowed_fields
        if unknown:
            raise serializers.ValidationError({"detail": f"Invalid limit. Valid limits are: {sorted(allowed_fields)}."})

        if not received_fields:
            raise serializers.ValidationError({"detail": "At least one field must be provided."})

        device_phones_amount = self.instance.barrier.device_phones_amount

        user_limit = attrs.get("user_phone_limit") or 0
        temp_limit = attrs.get("user_temp_phone_limit") or 0
        global_temp_limit = attrs.get("global_temp_phone_limit") or 0
        schedule_limit = attrs.get("user_schedule_phone_limit") or 0
        global_schedule_limit = attrs.get("global_schedule_phone_limit") or 0

        if (
            user_limit > device_phones_amount
            or temp_limit > device_phones_amount
            or global_temp_limit > device_phones_amount
            or schedule_limit > device_phones_amount
            or global_schedule_limit > device_phones_amount
        ):
            raise serializers.ValidationError({"detail": "Each limit must not exceed the amount of phones in device."})

        return super().validate(attrs)


class BarrierSettingParamSerializer(serializers.Serializer):
    name = serializers.CharField()
    key = serializers.CharField()
    example = serializers.CharField(required=False)
    description = serializers.CharField(required=False)


class BarrierSettingSerializer(serializers.Serializer):
    name = serializers.CharField()
    description = serializers.CharField(required=False)
    template = serializers.CharField()
    params = BarrierSettingParamSerializer(many=True)
    example = serializers.CharField(required=False)


class BarrierSettingsSerializer(serializers.Serializer):
    settings = serializers.DictField(child=BarrierSettingSerializer())


class SendBarrierSettingSerializer(serializers.Serializer):
    setting = serializers.CharField(required=True)
    params = serializers.DictField(child=serializers.CharField(), required=False, default=dict)
