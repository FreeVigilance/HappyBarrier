from rest_framework import serializers

from access_requests.models import AccessRequest
from barriers.models import UserBarrier


class AccessRequestSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()

    class Meta:
        model = AccessRequest
        fields = "__all__"

    def get_type(self, obj):
        """Determine request direction (incoming or outgoing) based on context"""

        as_admin = self.context.get("as_admin", False)

        if as_admin:
            return "outgoing" if obj.request_type == AccessRequest.RequestType.FROM_BARRIER else "incoming"
        else:
            return "outgoing" if obj.request_type == AccessRequest.RequestType.FROM_USER else "incoming"


class CreateAccessRequestSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new access request - by user or admin.
    Need to have `as_admin` set to `True` in context to serialize request as admin.
    """

    class Meta:
        model = AccessRequest
        fields = ["user", "barrier"]

    def validate(self, attrs):
        current_user = self.context["request"].user
        as_admin = self.context.get("as_admin", False)

        request_type = AccessRequest.RequestType.FROM_BARRIER if as_admin else AccessRequest.RequestType.FROM_USER
        attrs["request_type"] = request_type

        user = attrs["user"]
        barrier = attrs["barrier"]

        if not barrier.is_active:
            raise serializers.ValidationError({"error": "Cannot create access request for an inactive barrier."})

        if request_type == AccessRequest.RequestType.FROM_USER:
            if user != current_user:
                raise serializers.ValidationError({"error": "Users can only create requests for themselves."})
            if not barrier.is_public:
                raise serializers.ValidationError({"error": "Cannot request access to a private barrier."})
        else:
            if barrier.owner != current_user:
                raise serializers.ValidationError({"error": "You are not the owner of this barrier."})
            if not user.is_active:
                raise serializers.ValidationError({"error": "Cannot create access request for an inactive user."})

        # Check for existing pending request
        if AccessRequest.objects.filter(user=user, barrier=barrier, status=AccessRequest.Status.PENDING).exists():
            raise serializers.ValidationError({"error": "An active request already exists for this user and barrier."})

        # Check if user already has access
        if UserBarrier.objects.filter(user=user, barrier=barrier, is_active=True).exists():
            raise serializers.ValidationError({"error": "This user already has access to the barrier."})

        return attrs


class UpdateAccessRequestSerializer(serializers.ModelSerializer):
    """Serializer for updating access requests"""

    class Meta:
        model = AccessRequest
        fields = ["status", "hidden_for_user", "hidden_for_admin"]

    def validate(self, attrs):
        instance: AccessRequest = self.instance
        as_admin = self.context.get("as_admin", False)

        request_type = instance.request_type
        current_status = instance.status
        new_status = attrs.get("status", instance.status)

        allowed_transitions = AccessRequest.ALLOWED_STATUS_TRANSITIONS.get(current_status, set())
        if new_status != current_status and new_status not in allowed_transitions:
            raise serializers.ValidationError({"error": f"Invalid status transition: {current_status} -> {new_status}"})

        if new_status == AccessRequest.Status.CANCELLED:
            if (not as_admin and request_type == AccessRequest.RequestType.FROM_BARRIER) or (
                as_admin and request_type == AccessRequest.RequestType.FROM_USER
            ):
                raise serializers.ValidationError({"error": "You can only cancel your own requests."})

        if new_status in {AccessRequest.Status.ACCEPTED, AccessRequest.Status.REJECTED}:
            if (not as_admin and request_type == AccessRequest.RequestType.FROM_USER) or (
                as_admin and request_type == AccessRequest.RequestType.FROM_BARRIER
            ):
                raise serializers.ValidationError({"error": "You are not allowed to accept or reject this request."})

        if "hidden_for_admin" in attrs and not as_admin:
            raise serializers.ValidationError({"error": "Only admins can modify field 'hidden_for_admin'."})
        if "hidden_for_user" in attrs and as_admin:
            raise serializers.ValidationError({"error": "Only users can modify field 'hidden_for_user'."})

        return attrs
