import concurrent.futures
import logging
import signal
import threading
import time

from config import (
    DB_PATH,
    MODEM_PASSWORD,
    MODEM_URL,
    MODEM_USERNAME,
    NUMBER_OF_PARTITIONS,
    KafkaTopic,
)
from kafka.consumers import consume_loop
from kafka.handlers.configuration_handler import handle_sms_configuration
from kafka.handlers.verification_handler import handle_sms_verification
from modem.huawei_modem_client import HuaweiModemClient
from utils.logging import setup_logging

logger = logging.getLogger(__name__)
stop_event = threading.Event()

TOPIC_HANDLER_MAP = {
    KafkaTopic.SMS_VERIFICATION.value: handle_sms_verification,
    KafkaTopic.SMS_CONFIGURATION.value: handle_sms_configuration,
}


def signal_handler(signum, frame):
    logger.info("Received shutdown signal...")
    stop_event.set()


def main():
    logger.debug("Initializing Huawei modem client...")
    modem = HuaweiModemClient(url=MODEM_URL, db_path=DB_PATH, username=MODEM_USERNAME, password=MODEM_PASSWORD)

    # Thread pool for processing messages per partition
    logger.debug("Starting thread pool with %s workers", NUMBER_OF_PARTITIONS * len(TOPIC_HANDLER_MAP))
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=NUMBER_OF_PARTITIONS * len(TOPIC_HANDLER_MAP), thread_name_prefix="KafkaHandler"
    ) as executor:
        for topic_name, handler in TOPIC_HANDLER_MAP.items():
            for partition in range(NUMBER_OF_PARTITIONS):
                executor.submit(consume_loop, handler, partition, topic_name, modem, stop_event)

        logger.info("Service started. Listening for messages.")

        try:
            while not stop_event.is_set():
                time.sleep(1)
        finally:
            logger.info("Stopping executor...")
            stop_event.set()
            executor.shutdown(wait=True)


if __name__ == "__main__":
    setup_logging()
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    main()
