from rest_framework import serializers

from message_management.models import SMSMessage


class SMSMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SMSMessage
        exclude = ["phone", "metadata", "content"]
