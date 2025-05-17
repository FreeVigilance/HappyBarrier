import json
from unittest.mock import patch

import pytest
from confluent_kafka import KafkaException
from django.utils import timezone
from rest_framework.exceptions import APIException

from message_management.enums import KafkaTopic
from message_management.kafka_producer import send_sms_to_kafka
from message_management.models import SMSMessage
from phones.models import BarrierPhone


@pytest.mark.django_db
class TestKafkaProducer:

    @pytest.fixture
    def sms_message(self):
        return SMSMessage.objects.create(
            message_type=SMSMessage.MessageType.VERIFICATION_CODE,
            content="Test message",
            phone="+71234567890",
        )

    @patch("message_management.kafka_producer.get_producer")
    def test_send_sms_success(self, mock_get_producer, sms_message):
        producer_mock = mock_get_producer.return_value
        producer_mock.flush.return_value = 0

        send_sms_to_kafka(KafkaTopic.SMS_VERIFICATION, sms_message)

        sms_message.refresh_from_db()
        assert sms_message.status == SMSMessage.Status.SENT
        assert sms_message.updated_at <= timezone.now()

        producer_mock.produce.assert_called_once()
        args, kwargs = producer_mock.produce.call_args

        assert kwargs["topic"] == KafkaTopic.SMS_VERIFICATION.value
        assert kwargs["key"] == sms_message.phone
        payload = json.loads(kwargs["value"])
        assert payload == {
            "message_id": sms_message.id,
            "phone": sms_message.phone,
            "content": sms_message.content,
            "retries": 5,
        }

        producer_mock.flush.assert_called_once()

    @patch("message_management.kafka_producer.get_producer")
    def test_send_sms_flush_fails(self, mock_get_producer, sms_message):
        mock_get_producer.return_value.flush.return_value = 1

        with pytest.raises(APIException) as exc_info:
            send_sms_to_kafka(KafkaTopic.SMS_VERIFICATION, sms_message)

        sms_message.refresh_from_db()
        assert sms_message.status == SMSMessage.Status.FAILED
        assert sms_message.failure_reason == "Cannot connect to Kafka"
        assert "Cannot send SMS" in str(exc_info.value)

    @patch("message_management.kafka_producer.get_producer")
    def test_status_update_on_open_command(self, mock_get_producer, barrier_phone):
        phone, log = barrier_phone
        mock_get_producer.return_value.flush.return_value = 1
        sms = SMSMessage.objects.create(
            message_type=SMSMessage.MessageType.PHONE_COMMAND,
            content="OPEN GATE",
            phone=phone.barrier.device_phone,
            phone_command_type=SMSMessage.PhoneCommandType.OPEN,
            log=log,
        )

        with pytest.raises(Exception):
            send_sms_to_kafka(KafkaTopic.SMS_CONFIGURATION, sms)

        phone.refresh_from_db()
        assert phone.access_state == BarrierPhone.AccessState.ERROR_OPENING

    @patch("message_management.kafka_producer.get_producer")
    def test_status_update_on_close_command(self, mock_get_producer, barrier_phone):
        phone, log = barrier_phone
        mock_get_producer.return_value.flush.return_value = 1
        sms = SMSMessage.objects.create(
            message_type=SMSMessage.MessageType.PHONE_COMMAND,
            content="CLOSE GATE",
            phone=phone.barrier.device_phone,
            phone_command_type=SMSMessage.PhoneCommandType.CLOSE,
            log=log,
        )

        with pytest.raises(Exception):
            send_sms_to_kafka(KafkaTopic.SMS_CONFIGURATION, sms)

        phone.refresh_from_db()
        assert phone.access_state == BarrierPhone.AccessState.ERROR_CLOSING

    @patch("message_management.kafka_producer.get_producer")
    def test_producer_buffer_error(self, mock_get_producer, sms_message):
        producer_mock = mock_get_producer.return_value
        producer_mock.produce.side_effect = BufferError("Queue full")

        send_sms_to_kafka(KafkaTopic.SMS_VERIFICATION, sms_message)

        producer_mock.flush.assert_not_called()

    @patch("message_management.kafka_producer.get_producer")
    def test_producer_kafka_exception(self, mock_get_producer, sms_message):
        producer_mock = mock_get_producer.return_value
        producer_mock.produce.side_effect = KafkaException("Kafka down")

        send_sms_to_kafka(KafkaTopic.SMS_VERIFICATION, sms_message)

        producer_mock.flush.assert_not_called()

    @patch("message_management.kafka_producer.get_producer")
    def test_producer_unexpected_exception(self, mock_get_producer, sms_message):
        producer_mock = mock_get_producer.return_value
        producer_mock.produce.side_effect = RuntimeError("Unexpected error")

        send_sms_to_kafka(KafkaTopic.SMS_VERIFICATION, sms_message)

        producer_mock.flush.assert_not_called()
