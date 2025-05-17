from unittest.mock import patch

import pytest
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from action_history.models import BarrierActionLog
from message_management.enums import KafkaTopic, PhoneCommand
from message_management.models import SMSMessage
from message_management.services import BALANCE_CHECK_CONTENT, BALANCE_CHECK_PHONE, SMSService


@pytest.mark.django_db
class TestSendVerification:
    @patch("message_management.services.send_sms_to_kafka")
    def test_send_verification_success(self, mock_send_sms, create_verification):
        verification = create_verification()
        SMSService.send_verification(verification)

        message = SMSMessage.objects.get(message_type=SMSMessage.MessageType.VERIFICATION_CODE)

        mock_send_sms.assert_called_once_with(KafkaTopic.SMS_VERIFICATION, message)
        assert message.content.startswith("CODE:")


@pytest.mark.django_db
class TestSendAddPhoneCommand:
    @patch("message_management.services.send_sms_to_kafka")
    @patch("message_management.services.build_message", return_value="ADD_COMMAND")
    @patch("message_management.services.get_phone_command")
    def test_send_add_phone_command_success(self, mock_get_command, mock_build_message, mock_send_sms, barrier_phone):
        phone, log = barrier_phone
        mock_get_command.return_value = {"template": "{pwd}{index}{phone}"}

        SMSService.send_add_phone_command(phone, log)

        message = SMSMessage.objects.get(message_type=SMSMessage.MessageType.PHONE_COMMAND)

        mock_send_sms.assert_called_once_with(KafkaTopic.SMS_CONFIGURATION, message)
        mock_get_command.assert_called_once_with(phone.barrier.device_model, PhoneCommand.ADD)
        mock_build_message.assert_called_once()
        assert message.content == "ADD_COMMAND"
        assert message.phone_command_type == SMSMessage.PhoneCommandType.OPEN
        assert message.log == log


@pytest.mark.django_db
class TestSendDeletePhoneCommand:
    @patch("message_management.services.send_sms_to_kafka")
    @patch("message_management.services.build_message", return_value="DEL_COMMAND")
    @patch("message_management.services.get_phone_command")
    def test_send_delete_phone_command_success(
        self, mock_get_command, mock_build_message, mock_send_sms, barrier_phone
    ):
        phone, log = barrier_phone
        mock_get_command.return_value = {"template": "{pwd}{index}{phone}"}

        SMSService.send_delete_phone_command(phone, log)

        message = SMSMessage.objects.get(message_type=SMSMessage.MessageType.PHONE_COMMAND)

        mock_send_sms.assert_called_once_with(KafkaTopic.SMS_CONFIGURATION, message)
        mock_get_command.assert_called_once_with(phone.barrier.device_model, PhoneCommand.DELETE)
        mock_build_message.assert_called_once()
        assert message.content == "DEL_COMMAND"
        assert message.phone_command_type == SMSMessage.PhoneCommandType.CLOSE
        assert message.log == log


@pytest.mark.django_db
class TestGetAvailableSettings:
    def test_model_has_settings(self, barrier):
        result = SMSService.get_available_barrier_settings(barrier)
        assert "settings" in result
        assert isinstance(result["settings"], dict)

    def test_model_without_settings_raises(self, barrier):
        barrier.device_model = "UnknownModel"
        with pytest.raises(NotFound, match="No settings available for device model"):
            SMSService.get_available_barrier_settings(barrier)


@pytest.mark.django_db
class TestSendBarrierSetting:
    @pytest.fixture
    def log_entry(self, barrier):
        return BarrierActionLog.objects.create(
            barrier=barrier,
            author=BarrierActionLog.Author.ADMIN,
            action_type=BarrierActionLog.ActionType.BARRIER_SETTING,
        )

    @patch("message_management.services.send_sms_to_kafka")
    @patch("message_management.services.get_setting")
    def test_send_barrier_setting_success(self, mock_get_setting, mock_send_sms, barrier, log_entry):
        mock_get_setting.return_value = {"template": "{pwd}CMD", "params": [{"key": "pwd"}]}

        SMSService.send_barrier_setting(barrier, "start", {"pwd": "1234"}, log_entry)

        message = SMSMessage.objects.get(message_type=SMSMessage.MessageType.BARRIER_SETTING)

        mock_send_sms.assert_called_once_with(KafkaTopic.SMS_CONFIGURATION, message)
        mock_get_setting.assert_called_once_with(barrier.device_model, "start")
        assert message.content == "1234CMD"
        assert message.log == log_entry

    @patch("message_management.services.get_setting")
    def test_missing_required_params_raises(self, mock_get_setting, barrier, log_entry):
        mock_get_setting.return_value = {"template": "{pwd}CMD", "params": [{"key": "pwd"}, {"key": "extra"}]}

        with pytest.raises(ValidationError, match="Missing required parameters for barrier setting: extra"):
            SMSService.send_barrier_setting(barrier, "start", {"pwd": "1234"}, log_entry)

    @patch("message_management.services.get_setting")
    @patch("message_management.services.build_message", side_effect=ValidationError("Missing param"))
    def test_build_message_error(self, mock_build, mock_get_setting, barrier, log_entry):
        mock_get_setting.return_value = {"template": "{pwd}{unknown}", "params": [{"key": "pwd"}, {"key": "unknown"}]}

        with pytest.raises(ValidationError, match="Missing param"):
            SMSService.send_barrier_setting(barrier, "start", {"pwd": "1234", "unknown": ""}, log_entry)


@pytest.mark.django_db
class TestSendBalanceCheck:
    @patch("message_management.services.send_sms_to_kafka")
    def test_send_balance_check_success(self, mock_send_sms):
        SMSService.send_balance_check()

        message = SMSMessage.objects.get(message_type=SMSMessage.MessageType.BALANCE_CHECK)

        assert message.phone == BALANCE_CHECK_PHONE
        assert message.content == BALANCE_CHECK_CONTENT
        assert message.log is None
        mock_send_sms.assert_called_once_with(KafkaTopic.SMS_BALANCE, message)


@pytest.mark.django_db
class TestRetrySMSMessage:
    @pytest.fixture
    def original_sms(self, barrier_phone, sms_log):
        phone, _ = barrier_phone
        return SMSMessage.objects.create(
            message_type=SMSMessage.MessageType.PHONE_COMMAND,
            content="ORIGINAL",
            phone=phone.barrier.device_phone,
            metadata={"key": "value"},
            phone_command_type=SMSMessage.PhoneCommandType.OPEN,
            log=sms_log,
        )

    @patch("message_management.services.send_sms_to_kafka")
    @pytest.fixture
    def sms_log(self, barrier):
        return BarrierActionLog.objects.create(
            barrier=barrier,
            author=BarrierActionLog.Author.ADMIN,
            action_type=BarrierActionLog.ActionType.ADD_PHONE,
        )

    @patch("message_management.services.send_sms_to_kafka")
    def test_retry_phone_command_success(self, mock_send_sms, original_sms):
        new_sms = SMSService.retry_sms(original_sms)

        assert new_sms.id != original_sms.id
        assert new_sms.message_type == original_sms.message_type
        assert new_sms.phone == original_sms.phone
        assert new_sms.content == original_sms.content
        assert new_sms.metadata == original_sms.metadata
        assert new_sms.log == original_sms.log
        assert new_sms.phone_command_type == original_sms.phone_command_type

        mock_send_sms.assert_called_once_with(KafkaTopic.SMS_CONFIGURATION, new_sms)

    def test_retry_verification_forbidden(self):
        sms = SMSMessage(message_type=SMSMessage.MessageType.VERIFICATION_CODE)
        with pytest.raises(PermissionDenied, match="Cannot retry verification messages."):
            SMSService.retry_sms(sms)

    def test_retry_balance_check_forbidden(self):
        sms = SMSMessage(message_type=SMSMessage.MessageType.BALANCE_CHECK)
        with pytest.raises(PermissionDenied, match="Cannot retry verification messages."):
            SMSService.retry_sms(sms)

    def test_retry_unsupported_type(self):
        sms = SMSMessage(message_type="some_other_type")
        with pytest.raises(PermissionDenied, match="Unsupported SMS type for retry."):
            SMSService.retry_sms(sms)
