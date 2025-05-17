import concurrent.futures
import logging
import signal
import sys
import threading
import time

from django.core.management.base import BaseCommand

from message_management.enums import KafkaTopic
from message_management.kafka_consumer import KafkaConsumer

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(asctime)s | %(levelname)s | %(name)s | [%(threadName)s] | %(message)s",
)


logger = logging.getLogger(__name__)
stop_event = threading.Event()


def signal_handler(signum, frame):
    logger.info("Received shutdown signal...")
    stop_event.set()


class Command(BaseCommand):
    help = "Start Kafka consumers for SMS responses and failures"

    def handle(self, *args, **options):
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        response_consumer = KafkaConsumer(KafkaTopic.SMS_RESPONSES)
        failed_consumer = KafkaConsumer(KafkaTopic.FAILED_MESSAGES)

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            logger.info("Starting Kafka consumers for SMS")

            executor.submit(response_consumer.start)
            executor.submit(failed_consumer.start)

            logger.info("Consumers started. Waiting for stop signal.")

            try:
                while not stop_event.is_set():
                    time.sleep(1)
            finally:
                logger.info("Stopping consumers...")
                response_consumer.stop()
                failed_consumer.stop()
                executor.shutdown(wait=True)
