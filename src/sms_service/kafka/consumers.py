import logging
import threading
import time

from confluent_kafka import Consumer, Message, TopicPartition

from config import KAFKA_SERVERS
from modem.huawei_modem_client import HuaweiModemClient

logger = logging.getLogger(__name__)


def create_consumer(topic: str) -> Consumer:
    return Consumer(
        {
            "bootstrap.servers": KAFKA_SERVERS,
            "group.id": f"{topic}_group",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )


def initialize_consumer(topic_name: str, partition_id: int) -> Consumer:
    consumer = create_consumer(topic_name)
    consumer.assign([TopicPartition(topic_name, partition_id)])
    logger.debug(f"Assigned partition id: {partition_id} in topic: {topic_name}")
    return consumer


def consume_loop(handler, partition_id: int, topic_name: str, modem: HuaweiModemClient, stop_event: threading.Event):
    """Continuously listen for messages from a specific partition."""

    while not stop_event.is_set():
        try:
            consumer = initialize_consumer(topic_name, partition_id)

            while not stop_event.is_set():
                msg: Message = consumer.poll(timeout=10.0)
                if msg is None:
                    logger.debug(f"No new message in topic {topic_name} on partition {partition_id}. Waiting...")
                    continue
                if msg.error():
                    logger.error("Consumer error: %s", msg.error())
                    continue

                log_mgs = "Handling message %s from topic %s from partition %s at offset %s"
                logger.info(log_mgs, msg.value(), topic_name, partition_id, msg.offset())

                success = handler(modem, msg)
                if not success:
                    log_mgs = (
                        "Handler returned failure for message %s for topic %s for partition %s at offset %s. "
                        "Will recreate consumer."
                    )
                    logger.error(log_mgs, msg.value(), topic_name, partition_id, msg.offset())
                    raise Exception("Handler failure")

                consumer.commit(message=msg)
                log_mgs = "Commited successfully handled message from topic %s from partition %s at offset %s."
                logger.info(log_mgs, topic_name, partition_id, msg.offset())

        except Exception as e:
            log_mgs = "Error in consumer loop for topic %s on partition %s. Error: %s. Restarting in 5s..."
            logger.critical(log_mgs, topic_name, partition_id, e)

            try:
                consumer.close()
                logger.debug("Consumer closed successfully.")
            except Exception as close_error:
                logger.error("Error closing consumer: %s", close_error)

            time.sleep(5)  # delay before reconnecting
