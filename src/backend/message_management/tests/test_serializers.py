import pytest

from message_management.models import SMSMessage
from message_management.serializers import SMSMessageSerializer


@pytest.mark.django_db
class TestSMSMessageSerializer:
    def test_serializer_excludes_sensitive_fields(self, admin_user, barrier, create_barrier_phone):
        phone, log = create_barrier_phone(admin_user, barrier)

        sms = SMSMessage.objects.create(
            phone=phone.phone,
            message_type=SMSMessage.MessageType.PHONE_COMMAND,
            phone_command_type=SMSMessage.PhoneCommandType.OPEN,
            status=SMSMessage.Status.SENT,
            content="Some sensitive content",
            metadata={"pwd": "1234"},
            response_content="Some response",
            log=log,
        )

        serialized = SMSMessageSerializer(sms).data

        assert "phone" not in serialized
        assert "metadata" not in serialized
        assert "content" not in serialized

        assert serialized["id"] == sms.id
        assert serialized["message_type"] == SMSMessage.MessageType.PHONE_COMMAND
        assert serialized["phone_command_type"] == SMSMessage.PhoneCommandType.OPEN
        assert serialized["status"] == SMSMessage.Status.SENT
        assert serialized["response_content"] == "Some response"
        assert "sent_at" in serialized
        assert "updated_at" in serialized
