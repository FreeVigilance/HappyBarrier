import pytest
from django.core.exceptions import ValidationError

from message_management.models import SMSMessage


@pytest.mark.django_db
class TestSMSMessageModel:
    def test_sms_message_minimal_create(self, barrier_phone):
        phone, log = barrier_phone
        sms = SMSMessage.objects.create(
            phone=phone.phone, message_type=SMSMessage.MessageType.PHONE_COMMAND, content="open gate", log=log
        )
        assert sms.id is not None
        assert sms.status == SMSMessage.Status.CREATED

    def test_invalid_phone_format_raises(self):
        sms = SMSMessage(phone="12345", message_type=SMSMessage.MessageType.VERIFICATION_CODE, content="code: 1234")
        with pytest.raises(ValidationError):
            sms.full_clean()

    def test_default_status_is_created(self, barrier_phone):
        phone, _ = barrier_phone
        sms = SMSMessage.objects.create(
            phone=phone.phone, message_type=SMSMessage.MessageType.PHONE_COMMAND, content="Test"
        )
        assert sms.status == SMSMessage.Status.CREATED

    def test_optional_fields_can_be_empty(self, barrier_phone):
        phone, _ = barrier_phone
        sms = SMSMessage.objects.create(
            phone=phone.phone, message_type=SMSMessage.MessageType.PHONE_COMMAND, content="Silent"
        )
        assert sms.phone_command_type is None
        assert sms.metadata is None
        assert sms.response_content is None
        assert sms.failure_reason is None

    def test_sms_linked_to_log(self, barrier_phone):
        phone, log = barrier_phone
        sms = SMSMessage.objects.create(
            phone=phone.phone,
            message_type=SMSMessage.MessageType.PHONE_COMMAND,
            content="Go",
            log=log,
        )
        assert sms.log == log
        assert sms in log.sms_messages.all()
