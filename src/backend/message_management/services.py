import logging
import os

from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from action_history.models import BarrierActionLog
from barriers.models import Barrier
from message_management.config_loader import build_message, get_phone_command, get_setting, load_barrier_settings
from message_management.enums import KafkaTopic, PhoneCommand
from message_management.kafka_producer import send_sms_to_kafka
from message_management.models import SMSMessage
from phones.models import BarrierPhone
from verifications.models import Verification

logger = logging.getLogger(__name__)

BALANCE_CHECK_PHONE = os.getenv("BALANCE_CHECK_PHONE", "+70000000000")  # this will not be used
BALANCE_CHECK_CONTENT = os.getenv("BALANCE_CHECK_CONTENT", "*100#")  # this will not be used


class SMSService:
    """Service class for sending different types of SMS messages."""

    @staticmethod
    def send_verification(verification: Verification):
        message = SMSMessage.objects.create(
            message_type=SMSMessage.MessageType.VERIFICATION_CODE,
            content=f"CODE: {verification.code}",
            phone=verification.phone,
        )
        send_sms_to_kafka(KafkaTopic.SMS_VERIFICATION, message)

    @staticmethod
    def send_add_phone_command(phone: BarrierPhone, log: BarrierActionLog):
        SMSService._send_phone_command(phone, PhoneCommand.ADD, log)

    @staticmethod
    def send_delete_phone_command(phone: BarrierPhone, log: BarrierActionLog):
        SMSService._send_phone_command(phone, PhoneCommand.DELETE, log)

    @staticmethod
    def get_available_barrier_settings(barrier: Barrier) -> dict:
        all_settings = load_barrier_settings()
        logger.debug(f"Loaded barrier settings for model: '{barrier.device_model}'")
        model_settings = all_settings.get(barrier.device_model)

        if not model_settings:
            raise NotFound(f"No settings available for device model: '{barrier.device_model}'")

        return {"settings": model_settings}

    @staticmethod
    def send_barrier_setting(barrier: Barrier, setting_key: str, params: dict, log: BarrierActionLog):
        logger.info("Sending barrier setting '%s' for model '%s'", setting_key, barrier.device_model)
        setting = get_setting(barrier.device_model, setting_key)

        required_keys = [param["key"] for param in setting.get("params", [])]
        missing = [key for key in required_keys if key not in params]
        if missing:
            raise ValidationError({"detail": f"Missing required parameters for barrier setting: {', '.join(missing)}"})
        content = build_message(setting["template"], params)

        message = SMSMessage.objects.create(
            message_type=SMSMessage.MessageType.BARRIER_SETTING,
            content=content,
            phone=barrier.device_phone,
            metadata=params,
            log=log,
        )
        send_sms_to_kafka(KafkaTopic.SMS_CONFIGURATION, message)

    @staticmethod
    def _send_phone_command(phone: BarrierPhone, command: PhoneCommand, log: BarrierActionLog):
        barrier = phone.barrier

        command_config = get_phone_command(barrier.device_model, command)
        params = {
            "pwd": barrier.device_password,
            "phone": phone.phone.removeprefix("+7"),
            "index": phone.device_serial_number,
        }
        content = build_message(command_config["template"], params)
        phone_command_type = (
            SMSMessage.PhoneCommandType.OPEN if command == PhoneCommand.ADD else SMSMessage.PhoneCommandType.CLOSE
        )

        message = SMSMessage.objects.create(
            message_type=SMSMessage.MessageType.PHONE_COMMAND,
            content=content,
            phone=barrier.device_phone,
            metadata=params,
            phone_command_type=phone_command_type,
            log=log,
        )
        send_sms_to_kafka(KafkaTopic.SMS_CONFIGURATION, message)

    @staticmethod
    def send_balance_check():
        """
        Sends a USSD balance check command to the modem number.
        This is not a regular SMS, but it is tracked as SMSMessage for consistency.
        """

        logger.info("Sending balance check")

        message = SMSMessage.objects.create(
            message_type=SMSMessage.MessageType.BALANCE_CHECK,
            content=BALANCE_CHECK_CONTENT,  # this will not be used
            phone=BALANCE_CHECK_PHONE,  # this will not be used
        )
        send_sms_to_kafka(KafkaTopic.SMS_BALANCE, message)

    @staticmethod
    def retry_sms(original: SMSMessage) -> SMSMessage:
        if original.message_type in [SMSMessage.MessageType.VERIFICATION_CODE, SMSMessage.MessageType.BALANCE_CHECK]:
            raise PermissionDenied("Cannot retry verification messages.")

        message = SMSMessage.objects.create(
            phone=original.phone,
            message_type=original.message_type,
            phone_command_type=original.phone_command_type,
            content=original.content,
            metadata=original.metadata,
            log=original.log,
        )

        if message.message_type in [SMSMessage.MessageType.BARRIER_SETTING, SMSMessage.MessageType.PHONE_COMMAND]:
            topic = KafkaTopic.SMS_CONFIGURATION
        else:
            raise PermissionDenied("Unsupported SMS type for retry.")

        logger.info(f"Retrying SMS message {message.id} of type {message.message_type}")
        send_sms_to_kafka(topic, message)

        return message
