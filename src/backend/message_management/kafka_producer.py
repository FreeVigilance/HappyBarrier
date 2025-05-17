import json
import logging

from confluent_kafka import KafkaException, Producer
from django.utils.timezone import now
from rest_framework.exceptions import APIException

from message_management.constants import KAFKA_SERVERS
from message_management.enums import KafkaTopic
from message_management.models import SMSMessage
from phones.models import BarrierPhone

NUM_RETRIES = 5
_producer = None

logger = logging.getLogger(__name__)


def get_producer() -> Producer:
    global _producer
    if _producer is None:
        _producer = Producer({"bootstrap.servers": KAFKA_SERVERS})
    return _producer


def reset_producer():
    global _producer
    logger.warning("Resetting Kafka producer")
    _producer = None


def send_sms_to_kafka(topic: KafkaTopic, message: SMSMessage):
    payload = {
        "message_id": message.id,
        "phone": message.phone,
        "content": message.content,
        "retries": NUM_RETRIES,
    }

    try:
        producer = get_producer()
        producer.produce(
            topic=topic.value,
            key=message.phone,
            value=json.dumps(payload),
        )
        n = producer.flush(timeout=1)
        if n != 0:
            logger.error("Kafka flush failed: message may not have been delivered")
            message.status = SMSMessage.Status.FAILED
            message.failure_reason = "Cannot connect to Kafka"
            message.updated_at = now()
            message.save()

            if message.message_type == SMSMessage.MessageType.PHONE_COMMAND and message.log and message.log.phone:
                phone = message.log.phone
                if message.phone_command_type == SMSMessage.PhoneCommandType.OPEN:
                    phone.access_state = BarrierPhone.AccessState.ERROR_OPENING
                elif message.phone_command_type == SMSMessage.PhoneCommandType.CLOSE:
                    phone.access_state = BarrierPhone.AccessState.ERROR_CLOSING
                phone.save()

            raise ConnectionError("Failed to deliver message to Kafka")
        logger.info("SMS sent to Kafka topic %s for phone %s", topic.value, message.phone)

    except ConnectionError:
        raise APIException("Cannot send SMS. Try again later")

    except BufferError as e:
        logger.error("Kafka producer queue is full: %s", e)
        reset_producer()

    except KafkaException as e:
        logger.error("Kafka exception occurred: %s", e)
        reset_producer()

    except Exception as e:
        logger.exception(f"Unexpected error while producing to Kafka: {e}")
        reset_producer()

    message.status = SMSMessage.Status.SENT
    message.updated_at = now()
    message.save()
