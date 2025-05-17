import json
import logging
import re
import threading
import time

from confluent_kafka import Consumer, Message

from action_history.models import BarrierActionLog
from barriers.models import Barrier
from message_management.config_loader import get_phone_command
from message_management.constants import KAFKA_SERVERS
from message_management.enums import KafkaTopic, PhoneCommand
from message_management.models import SMSMessage
from phones.models import BarrierPhone

logger = logging.getLogger(__name__)


class SMSMessageHandlers:
    @staticmethod
    def _parse_message_data(message: Message) -> tuple[int | None, str]:
        try:
            value = message.value()
            if value is None:
                logger.warning("Received Kafka message with no value.")
                return None, ""

            data = json.loads(value.decode("utf-8"))
            return data.get("message_id"), data.get("content", "")
        except Exception as e:
            logger.exception("Failed to parse Kafka message: %s", e)
            return None, ""

    @staticmethod
    def _load_sms(message_id: int) -> SMSMessage | None:
        try:
            return SMSMessage.objects.get(id=message_id)
        except SMSMessage.DoesNotExist:
            logger.warning("SMS message %s not found", message_id)
            return None

    @staticmethod
    def _process_phone_command(sms: SMSMessage, content: str):
        content = content.strip().splitlines()[0]
        logger.info("Content: %s", content)

        if not sms.log:
            logger.error("SMS %s has no associated log.", sms.id)
            sms.status = SMSMessage.Status.FAILED
            return

        phone: BarrierPhone = sms.log.phone
        success = False
        logger.info(f"Phone: {phone}, log: {sms.log}")

        try:
            barrier: Barrier = sms.log.barrier
            log_action: BarrierActionLog.ActionType = sms.log.action_type
            phone_command = PhoneCommand(log_action)
            pattern = get_phone_command(barrier.device_model, phone_command).get("response_pattern")
            logger.info(f"Barrier: {barrier}, command: {phone_command}, pattern: {pattern}")

            if not pattern:
                logger.error("No pattern found for model=%s command=%s", barrier.device_model, phone_command)
                sms.status = SMSMessage.Status.FAILED
            elif re.match(pattern, content):
                sms.status = SMSMessage.Status.SUCCESS
                success = True
            else:
                logger.info(f"NO PATTERN MATCHED: {pattern} = {content}")
                sms.status = SMSMessage.Status.FAILED
        except Exception as e:
            logger.exception("Error parsing command response for SMS %s: %s", sms.id, e)
            sms.status = SMSMessage.Status.FAILED

        logger.info(f"CHECKING PHONE: {phone}")
        if sms.phone_command_type == SMSMessage.PhoneCommandType.OPEN:
            phone.access_state = BarrierPhone.AccessState.OPEN if success else BarrierPhone.AccessState.ERROR_OPENING
        elif sms.phone_command_type == SMSMessage.PhoneCommandType.CLOSE:
            phone.access_state = BarrierPhone.AccessState.CLOSED if success else BarrierPhone.AccessState.ERROR_CLOSING

        logger.info(f"SAVING PHONE: {phone}")
        phone.save()

    @staticmethod
    def handle_failed_message(message: Message) -> bool:
        message_id, content = SMSMessageHandlers._parse_message_data(message)
        if not message_id:
            return False

        sms = SMSMessageHandlers._load_sms(message_id)
        if not sms:
            return False

        sms.status = SMSMessage.Status.FAILED
        sms.response_content = content
        sms.save()

        if sms.message_type == SMSMessage.MessageType.PHONE_COMMAND and sms.log and sms.log.phone:
            phone = sms.log.phone
            logger.info("Marking phone access_state as failed for SMS %s", sms.id)

            if sms.phone_command_type == SMSMessage.PhoneCommandType.OPEN:
                phone.access_state = BarrierPhone.AccessState.ERROR_OPENING
            elif sms.phone_command_type == SMSMessage.PhoneCommandType.CLOSE:
                phone.access_state = BarrierPhone.AccessState.ERROR_CLOSING

            phone.save()

        logger.info("Marked SMS %s as FAILED", sms.id)
        return True

    @staticmethod
    def handle_response_message(message: Message) -> bool:
        message_id, content = SMSMessageHandlers._parse_message_data(message)
        if not message_id:
            return False

        sms = SMSMessageHandlers._load_sms(message_id)
        if not sms:
            return False

        logger.info("Processing response for SMS %s", sms.id)

        if sms.message_type == SMSMessage.MessageType.PHONE_COMMAND:
            SMSMessageHandlers._process_phone_command(sms, content)

        elif sms.message_type == SMSMessage.MessageType.BARRIER_SETTING:
            sms.status = SMSMessage.Status.SUCCESS

        else:
            logger.info("Ignoring SMS %s of type %s", sms.id, sms.message_type)
            return True

        sms.response_content = content
        sms.save()
        logger.info("Updated SMS %s with status %s", sms.id, sms.status)
        return True


class KafkaConsumer:
    TOPIC_HANDLERS = {
        KafkaTopic.SMS_RESPONSES: SMSMessageHandlers.handle_response_message,
        KafkaTopic.FAILED_MESSAGES: SMSMessageHandlers.handle_failed_message,
    }

    def __init__(self, topic: KafkaTopic):
        self.topic = topic
        self.handler = self.TOPIC_HANDLERS.get(topic)
        self.stop_event = threading.Event()
        self.consumer = self._create_consumer()

    def _create_consumer(self) -> Consumer:
        consumer = Consumer(
            {
                "bootstrap.servers": KAFKA_SERVERS,
                "group.id": f"sms_handler_{self.topic.value}_group",
                "auto.offset.reset": "earliest",
                "enable.auto.commit": False,
            }
        )
        consumer.subscribe([self.topic.value])
        logger.info(f"Created consumer and subscribed to topic: {self.topic}")
        return consumer

    def _restart(self):
        try:
            self.consumer.close()
        except Exception as e:
            logger.error("Error closing consumer: %s", e)
        time.sleep(5)
        self.consumer = self._create_consumer()

    def stop(self):
        self.stop_event.set()
        logger.info("Stopping Kafka consumer")

    def start(self):
        logger.info(f"Starting consumer for topic {self.topic}")
        while not self.stop_event.is_set():
            try:
                msg: Message = self.consumer.poll(timeout=5.0)
                if msg is None:
                    logger.debug(f"No message on {self.topic}. Continuing...")
                    continue
                if msg.error():
                    logger.error(f"Error receiving message on {self.topic}: {msg.error()}")
                logger.info(f"Received message: {msg.value()} on {self.topic}")
                if self.handler(msg):
                    self.consumer.commit(msg)
                    logger.info(f"Committed message at offset {msg.offset()}")
                else:
                    raise Exception("Handler failed")

            except Exception as e:
                logger.critical(f"Consumer error on topic {self.topic}: {e}")
                self._restart()
