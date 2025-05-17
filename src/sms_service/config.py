import os
from enum import Enum

KAFKA_SERVERS = os.getenv("KAFKA_SERVERS", "localhost:19092")


class KafkaTopic(Enum):
    SMS_CONFIGURATION = "sms_configuration"
    SMS_VERIFICATION = "sms_verification"
    SMS_BALANCE = "sms_balance"
    SMS_RESPONSES = "sms_responses"
    FAILED_MESSAGES = "failed_messages"


NUMBER_OF_PARTITIONS = int(os.getenv("NUMBER_OF_PARTITIONS", "3"))

DB_PATH = os.getenv("DB_PATH", "sms_storage.sqlite3")

MODEM_USERNAME = os.getenv("MODEM_USERNAME", "admin")
MODEM_PASSWORD = os.getenv("MODEM_PASSWORD", "password")
MODEM_URL = f"http://{MODEM_USERNAME}:{MODEM_PASSWORD}@192.168.8.1/"

MESSAGE_RESPONSE_TIMEOUT_SECONDS = int(os.getenv("MESSAGE_RESPONSE_TIMEOUT_SECONDS", 600))