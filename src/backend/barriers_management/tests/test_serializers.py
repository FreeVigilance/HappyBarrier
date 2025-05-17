import copy
from unittest.mock import patch

import pytest

from barriers.models import Barrier, BarrierLimit
from barriers_management.serializers import (
    AdminBarrierSerializer,
    BarrierSettingsSerializer,
    CreateBarrierSerializer,
    SendBarrierSettingSerializer,
    UpdateBarrierLimitSerializer,
    UpdateBarrierSerializer,
)
from conftest import BARRIER_ADDRESS, BARRIER_DEVICE_PASSWORD, BARRIER_DEVICE_PHONE
from core.utils import ConflictError


@pytest.mark.django_db
class TestAdminBarrierSerializer:
    def test_excludes_password(self, barrier):
        serializer = AdminBarrierSerializer(barrier)
        data = serializer.data

        assert "device_password" not in data
        assert data["address"] == barrier.address


@pytest.mark.django_db
class TestCreateBarrierSerializer:
    data = {
        "address": BARRIER_ADDRESS,
        "device_phone": BARRIER_DEVICE_PHONE,
        "device_model": Barrier.Model.RTU5025,
        "device_phones_amount": 2,
        "device_password": BARRIER_DEVICE_PASSWORD,
        "additional_info": "Testing description",
        "is_public": True,
    }

    @pytest.fixture
    def admin_context(self, admin_user):
        """Returns serializer context with admin user in request."""

        return {"request": type("Request", (), {"user": admin_user})()}

    def test_valid_data(self, admin_user, admin_context):
        serializer = CreateBarrierSerializer(data=self.data, context=admin_context)

        assert serializer.is_valid(), serializer.errors
        barrier = serializer.save()

        assert barrier.owner == admin_user
        assert barrier.device_phone == BARRIER_DEVICE_PHONE
        assert barrier.address == BARRIER_ADDRESS

    def test_invalid_phone(self, barrier, admin_context):
        data = copy.deepcopy(self.data)
        data["device_phone"] = barrier.device_phone

        with pytest.raises(ConflictError) as exc_info:
            serializer = CreateBarrierSerializer(data=data, context=admin_context)
            serializer.is_valid(raise_exception=True)

        assert str(exc_info.value) == "This phone is already taken by another barrier."

    def test_invalid_amount(self, admin_context):
        data = copy.deepcopy(self.data)
        data["device_phones_amount"] = 0

        serializer = CreateBarrierSerializer(data=data, context=admin_context)

        assert not serializer.is_valid()
        assert "device_phones_amount" in serializer.errors

    def test_missing_password_for_some_models(self, admin_context):
        data = copy.deepcopy(self.data)
        data["device_password"] = ""

        serializer = CreateBarrierSerializer(data=data, context=admin_context)

        assert not serializer.is_valid()
        assert serializer.errors["device_password"][0] == "Device password is required for this device model."

    def test_invalid_password_format(self, admin_context):
        data = copy.deepcopy(self.data)
        data["device_password"] = "abcd"

        serializer = CreateBarrierSerializer(data=data, context=admin_context)

        assert not serializer.is_valid()
        assert serializer.errors["device_password"][0] == "Enter a valid device password. Must be exactly 4 digits."

    def test_no_password_for_some_models(self, admin_context):
        data = copy.deepcopy(self.data)
        data["device_model"] = Barrier.Model.TELEMETRICA
        data["device_password"] = ""

        serializer = CreateBarrierSerializer(data=data, context=admin_context)

        assert serializer.is_valid()

    @patch("barriers_management.serializers.get_phone_command")
    def test_unsupported_device_model(self, mock_get_phone_command, admin_context):
        mock_get_phone_command.side_effect = Exception("Command not supported")

        data = {
            "address": "Test address",
            "device_phone": "+79990000001",
            "device_model": "RTU5025",
            "device_phones_amount": 1,
            "device_password": "1234",
            "additional_info": "info",
            "is_public": True,
        }

        serializer = CreateBarrierSerializer(data=data, context=admin_context)

        assert not serializer.is_valid()
        assert "device_model" in serializer.errors
        assert "Command not supported" in serializer.errors["device_model"][0]
        assert mock_get_phone_command.call_count == 1


@pytest.mark.django_db
class TestUpdateBarrierSerializer:
    def test_partial_update(self, barrier):
        data = {
            "device_password": BARRIER_DEVICE_PASSWORD,
            "additional_info": "Updated info",
        }

        serializer = UpdateBarrierSerializer(instance=barrier, data=data, partial=True)
        assert serializer.is_valid(), serializer.errors
        updated = serializer.save()

        assert updated.device_password == BARRIER_DEVICE_PASSWORD
        assert updated.additional_info == "Updated info"

    def test_invalid_password_format(self, barrier):
        data = {"device_password": "abcd"}

        serializer = UpdateBarrierSerializer(instance=barrier, data=data, partial=True)

        assert not serializer.is_valid()
        assert "Enter a valid device password. Must be exactly 4 digits." in serializer.errors["device_password"]


@pytest.mark.django_db
class TestUpdateBarrierLimitSerializer:
    def test_valid_update(self, barrier):
        limit = BarrierLimit.objects.create(barrier=barrier)
        data = {
            "user_phone_limit": 5,
            "sms_weekly_limit": 20,
        }

        serializer = UpdateBarrierLimitSerializer(limit, data=data, partial=True)
        assert serializer.is_valid(), serializer.errors
        result = serializer.save()

        assert result.user_phone_limit == 5
        assert result.sms_weekly_limit == 20

    def test_null_values_allowed(self, barrier):
        limit = BarrierLimit.objects.create(barrier=barrier, sms_weekly_limit=10)
        data = {"sms_weekly_limit": None}

        serializer = UpdateBarrierLimitSerializer(limit, data=data, partial=True)
        assert serializer.is_valid(), serializer.errors
        result = serializer.save()

        assert result.sms_weekly_limit is None

    def test_negative_value_not_allowed(self, barrier):
        limit = BarrierLimit.objects.create(barrier=barrier)
        data = {"user_temp_phone_limit": -1}

        serializer = UpdateBarrierLimitSerializer(limit, data=data, partial=True)
        assert not serializer.is_valid()
        assert "user_temp_phone_limit" in serializer.errors

    def test_unexpected_fields_raises_error(self, barrier):
        limit = BarrierLimit.objects.create(barrier=barrier)
        data = {"invalid_field": 1}

        serializer = UpdateBarrierLimitSerializer(limit, data=data, partial=True)
        assert not serializer.is_valid()
        assert "Invalid limit. Valid limits are: " in serializer.errors["detail"][0]

    def test_empty_payload_raises_error(self, barrier):
        limit = BarrierLimit.objects.create(barrier=barrier)
        data = {}

        serializer = UpdateBarrierLimitSerializer(limit, data=data, partial=True)
        assert not serializer.is_valid()
        assert "At least one field must be provided." in serializer.errors["detail"]

    def test_limit_exceeds_device_capacity(self, barrier):
        barrier.device_phones_amount = 5
        barrier.save()

        limit = BarrierLimit.objects.create(barrier=barrier)
        data = {"user_phone_limit": 6}

        serializer = UpdateBarrierLimitSerializer(limit, data=data, partial=True)
        assert not serializer.is_valid()
        assert "Each limit must not exceed the amount of phones in device." in serializer.errors["detail"][0]


class TestBarrierSettingsSerializer:
    def test_valid_structure(self):
        data = {
            "settings": {
                "start": {
                    "name": "Начало",
                    "description": "Описание",
                    "template": "{pwd}CMD",
                    "params": [{"name": "Пароль", "key": "pwd", "example": "1234", "description": "some text"}],
                    "example": "1234CMD",
                }
            }
        }

        serializer = BarrierSettingsSerializer(data=data)
        assert serializer.is_valid(), serializer.errors


class TestSendBarrierSettingSerializer:
    def test_valid_data(self):
        data = {"setting": "start", "params": {"pwd": "1234"}}

        serializer = SendBarrierSettingSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_params_is_not_dict(self):
        data = {"setting": "start", "params": ["not", "a", "dict"]}

        serializer = SendBarrierSettingSerializer(data=data)
        assert not serializer.is_valid()
        assert serializer.errors["params"][0].code == "not_a_dict"

    def test_params_dict_wrong_value(self):
        data = {"setting": "start", "params": {"key": ["array"]}}

        serializer = SendBarrierSettingSerializer(data=data)
        assert not serializer.is_valid()
        assert "params" in serializer.errors

    def test_setting_is_required(self):
        data = {"params": {"pwd": "1234"}}

        serializer = SendBarrierSettingSerializer(data=data)
        assert not serializer.is_valid()
        assert "setting" in serializer.errors
