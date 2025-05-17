from django.db import models

from action_history.models import BarrierActionLog
from core.constants import CHOICE_MAX_LENGTH, PHONE_MAX_LENGTH
from core.validators import PhoneNumberValidator


class SMSMessage(models.Model):
    class Meta:
        db_table = "sms_message"

    class MessageType(models.TextChoices):
        VERIFICATION_CODE = "verification", "Verification Code"
        PHONE_COMMAND = "phone_command", "Phone Command"
        BARRIER_SETTING = "barrier_setting", "Barrier Setting"
        BALANCE_CHECK = "balance_check", "Balance Check"

    class PhoneCommandType(models.TextChoices):
        OPEN = "open", "Open Access"
        CLOSE = "close", "Close Access"

    class Status(models.TextChoices):
        CREATED = "created", "Waiting for sending"
        SENT = "sent", "Sent"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    phone = models.CharField(
        max_length=PHONE_MAX_LENGTH,
        db_index=True,
        validators=[PhoneNumberValidator()],
        help_text="Enter a phone number in the format +7XXXXXXXXXX.",
    )
    message_type = models.CharField(max_length=CHOICE_MAX_LENGTH, choices=MessageType.choices)
    phone_command_type = models.CharField(
        max_length=CHOICE_MAX_LENGTH, choices=PhoneCommandType.choices, null=True, blank=True
    )
    status = models.CharField(max_length=CHOICE_MAX_LENGTH, choices=Status.choices, default=Status.CREATED)

    content = models.TextField()
    metadata = models.JSONField(null=True, blank=True)
    response_content = models.TextField(null=True, blank=True)
    failure_reason = models.TextField(null=True, blank=True)

    sent_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Reverse link to ActionHistory
    log = models.ForeignKey(
        BarrierActionLog,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sms_messages",
        help_text="Action that triggered this message, if applicable.",
    )
