from rest_framework import serializers

from barriers.models import Barrier, BarrierLimit
from barriers.validators import DevicePasswordValidator


class AdminBarrierSerializer(serializers.ModelSerializer):
    """Serializer for viewing a barrier from the admin's perspective"""

    class Meta:
        model = Barrier
        exclude = ("device_password",)


class CreateBarrierSerializer(serializers.ModelSerializer):
    """Serializer for creating a new barrier"""

    additional_info = serializers.CharField(required=True, allow_blank=True)
    device_phones_amount = serializers.IntegerField(required=True)

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

    def validate_address(self, value):
        """Convert the address to lowercase"""

        return value.lower().strip()

    def validate_device_phone(self, value):
        """Check if a device with the given phone number already exists"""

        if Barrier.objects.filter(device_phone=value, is_active=True).exists():
            raise serializers.ValidationError({"error": "A barrier with this phone number already exists."})
        return value

    def validate_device_phones_amount(self, value):
        """Ensure `device_phones_amount` is greater than 0"""

        if value <= 0:
            raise serializers.ValidationError({"error": "The number of device phone slots must be greater than 0."})
        return value

    def validate(self, attrs):
        """Conditional password validation based on device model"""

        model = attrs["device_model"]
        password = attrs.get("device_password")

        if model != Barrier.Model.TELEMETRICA:
            if not password:
                raise serializers.ValidationError({"error": "Device password is required for this device model."})

            DevicePasswordValidator()(password)

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
                DevicePasswordValidator()(password)

        return attrs


class UpdateBarrierLimitSerializer(serializers.ModelSerializer):
    """Serializer for updating/creating barrier limits"""

    user_phone_limit = serializers.IntegerField(min_value=0, allow_null=True, required=False)
    user_temp_phone_limit = serializers.IntegerField(min_value=0, allow_null=True, required=False)
    global_temp_phone_limit = serializers.IntegerField(min_value=0, allow_null=True, required=False)
    sms_weekly_limit = serializers.IntegerField(min_value=0, allow_null=True, required=False)

    class Meta:
        model = BarrierLimit
        fields = [
            "user_phone_limit",
            "user_temp_phone_limit",
            "global_temp_phone_limit",
            "sms_weekly_limit",
        ]

    def validate(self, attrs):
        allowed_fields = set(self.fields.keys())
        received_fields = set(self.initial_data.keys())

        unknown = received_fields - allowed_fields
        if unknown:
            raise serializers.ValidationError({"error": f"Unexpected fields: {', '.join(sorted(unknown))}"})

        if not received_fields:
            raise serializers.ValidationError({"error": "At least one field must be provided."})

        device_phones_amount = self.instance.barrier.device_phones_amount

        user_limit = attrs.get("user_phone_limit") or 0
        temp_limit = attrs.get("user_temp_phone_limit") or 0
        global_temp_limit = attrs.get("global_temp_phone_limit") or 0

        if (
            user_limit > device_phones_amount
            or temp_limit > device_phones_amount
            or global_temp_limit > device_phones_amount
        ):
            raise serializers.ValidationError({"error": "Each limit must not exceed the amount of phones in device."})

        return super().validate(attrs)
