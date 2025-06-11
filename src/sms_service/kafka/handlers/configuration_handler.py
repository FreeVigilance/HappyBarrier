import json
import logging
import time

from confluent_kafka import Message

from config import MESSAGE_RESPONSE_TIMEOUT_SECONDS
from kafka.producer import send_to_failed, send_to_responses
from modem.huawei_modem_client import HuaweiModemClient

logger = logging.getLogger("__name__")

MAX_DELAY_SECONDS = 3600


def wait_for_reply_from_phone(modem: HuaweiModemClient, phone: str, start_ts: float):
    """Wait for an incoming SMS reply from the given phone number, after a specific time within the timeout."""

    logger.debug("Waiting for reply from phone: %s", phone)

    start = time.time()
    while time.time() - start < MESSAGE_RESPONSE_TIMEOUT_SECONDS:
        reply = modem.get_reply_from_phone_since(phone, start_ts)
        if reply:
            logger.info("Received reply from phone: %s", phone)
            return reply
        time.sleep(10)

    logger.warning("Timeout waiting for reply from phone: %s", phone)
    return None


def handle_sms_configuration(modem: HuaweiModemClient, message: Message) -> bool:
    try:
        value = message.value()
        if value is None:
            logger.warning("Received message with no value.")
            return False

        data = json.loads(value.decode("utf-8"))
        phone = data["phone"]
        content = data["content"]
        retries = data["retries"]
        message_id = data["message_id"]
        created_at = data.get("timestamp")

        logger.info("Handling configuration SMS for phone: %s", phone)

        if created_at:
            age = time.time() - created_at
            if age > MAX_DELAY_SECONDS:
                logger.warning("Skipping SMS to %s: message too old (%d seconds)", phone, age)
                send_to_failed({"message_id": message_id, "phone": phone, "content": "Too old"}, phone)
                return True

        for attempt in range(retries):
            logger.debug("Attempt %d to send configuration SMS to %s", attempt + 1, phone)
            success = modem.send_sms(phone, content)
            sent_ts = time.time()
            if success:
                logger.info("Configuration SMS sent to %s, now waiting for reply...", phone)
                break  # Exit cycle after successful send
            logger.error("Failed to send configuration SMS to %s, attempt %d", phone, attempt + 1)
        else:
            # <-- Error after all attempts
            logger.error("All attempts to send SMS failed for phone: %s, sending to failed_messages topic", phone)
            send_to_failed(data, phone)
            return False

        reply = wait_for_reply_from_phone(modem, phone, start_ts=sent_ts)
        if reply:
            logger.info("Reply received from %s, sending to responses topic", phone)
            send_to_responses({"message_id": message_id, "phone": phone, "content": reply}, phone)
            return True
        else:
            logger.warning("No reply received from phone: %s", phone)
            send_to_failed(data, phone)
            return False

    except Exception as e:
        logger.exception("Unexpected error while handling configuration SMS: %s", e)
        return False  # <-- Any unexpected error
