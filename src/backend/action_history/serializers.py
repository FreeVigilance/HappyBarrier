from rest_framework import serializers

from message_management.models import BarrierActionLog


class BarrierActionLogSerializer(serializers.ModelSerializer):

    class Meta:
        model = BarrierActionLog
        fields = "__all__"
