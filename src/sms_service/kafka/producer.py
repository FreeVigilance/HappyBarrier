import json
import logging

from confluent_kafka import Producer

from config import KAFKA_SERVERS, KafkaTopic

logger = logging.getLogger(__name__)

producer = Producer({"bootstrap.servers": KAFKA_SERVERS})


def send_to_responses(payload: dict, phone: str) -> None:
    logger.debug("Sending message to sms_responses topic for phone: %s", phone)
    producer.produce(KafkaTopic.SMS_RESPONSES.value, key=phone, value=json.dumps(payload))
    producer.flush()
    logger.info("Message sent to sms_responses for phone: %s", phone)


def send_to_failed(payload: dict, phone: str) -> None:
    logger.debug("Sending message to failed_messages topic for phone: %s", phone)
    producer.produce(KafkaTopic.FAILED_MESSAGES.value, key=phone, value=json.dumps(payload))
    producer.flush()
    logger.info("Message sent to failed_messages for phone: %s", phone)
