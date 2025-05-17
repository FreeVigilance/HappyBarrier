from enum import Enum


class PhoneCommand(Enum):
    ADD = "add_phone"
    DELETE = "delete_phone"

    @classmethod
    def choices(cls):
        return [(member.value, member.name) for member in cls]


class KafkaTopic(Enum):
    SMS_CONFIGURATION = "sms_configuration"
    SMS_VERIFICATION = "sms_verification"
    SMS_BALANCE = "sms_balance"
    SMS_RESPONSES = "sms_responses"
    FAILED_MESSAGES = "failed_messages"

    @classmethod
    def choices(cls):
        return [(member.value, member.name) for member in cls]
