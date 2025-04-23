import logging

from rest_framework import serializers

from barriers.models import Barrier, BarrierLimit, UserBarrier
from users.models import User

logger = logging.getLogger(__name__)


class BarrierSerializer(serializers.ModelSerializer):
    """Barrier serializer with respect to data privacy settings"""

    owner = serializers.SerializerMethodField()
    device_phone = serializers.SerializerMethodField()

    class Meta:
        model = Barrier
        fields = ["id", "address", "owner", "is_active", "device_phone", "additional_info"]

    def get_owner(self, obj):
        """Returns owner info depending on `phone_privacy` setting"""

        if not obj.owner:
            return None

        request = self.context.get("request")
        request_user = getattr(request, "user", None)
        owner_data = {
            "id": obj.owner.id,
            "full_name": obj.owner.full_name,
            "phone": None,
        }

        # Show phone number if it's public
        if obj.owner.phone_privacy == User.PhonePrivacy.PUBLIC:
            owner_data["phone"] = obj.owner.phone
        elif obj.owner.phone_privacy == User.PhonePrivacy.PROTECTED:
            if request_user and UserBarrier.user_has_access_to_barrier(request_user, obj):
                owner_data["phone"] = obj.owner.phone

        return owner_data

    def get_device_phone(self, obj):
        """Determines whether device_phone can be shown"""

        request = self.context.get("request")
        request_user = request.user

        # Show if user has access to this barrier
        if request_user and UserBarrier.user_has_access_to_barrier(request_user, obj):
            return obj.device_phone

        return None  # Hide by default


class BarrierLimitSerializer(serializers.ModelSerializer):
    class Meta:
        model = BarrierLimit
        exclude = ["id", "created_at", "updated_at"]
