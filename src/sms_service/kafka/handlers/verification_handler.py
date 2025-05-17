import json
import logging

from confluent_kafka import Message

from kafka.producer import send_to_failed
from modem.huawei_modem_client import HuaweiModemClient

logger = logging.getLogger("__name__")


def handle_sms_verification(modem: HuaweiModemClient, message: Message) -> bool:
    try:
        value = message.value()
        if value is None:
            logger.warning("Received message with no value.")
            return False

        data = json.loads(value.decode("utf-8"))
        phone = data["phone"]
        content = data["content"]
        retries = data["retries"]

        logger.debug("Handling verification SMS for phone: %s, data: %s", phone, data)

        for attempt in range(retries):
            logger.debug("Attempt %d to send verification SMS to %s", attempt + 1, phone)
            success = modem.send_sms(phone, content)
            if success:
                logger.debug("Verification SMS sent to %s", phone)
                return True  # <-- Success

            logger.error("Failed to send verification SMS to %s, attempt %d", phone, attempt + 1)

        logger.error("All attempts failed for phone: %s, sending to failed_messages topic", phone)
        send_to_failed(data, phone)
        return True  # <-- Error after all attempts

    except Exception as e:
        logger.error("Unexpected error while handling SMS: %s", e)
        return False  # <-- Any unexpected error
