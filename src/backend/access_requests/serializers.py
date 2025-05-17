from rest_framework import serializers
from rest_framework.exceptions import NotFound, PermissionDenied

from access_requests.models import AccessRequest
from barriers.models import UserBarrier
from core.utils import ConflictError


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

    def to_internal_value(self, data):
        try:
            return super().to_internal_value(data)
        except serializers.ValidationError as exc:
            errors = exc.detail
            for field, messages in errors.items():
                if any("does not exist" in str(msg) for msg in messages):
                    raise NotFound(f"{field.capitalize()} not found.")
            raise

    def validate(self, attrs):
        current_user = self.context["request"].user
        as_admin = self.context.get("as_admin", False)

        request_type = AccessRequest.RequestType.FROM_BARRIER if as_admin else AccessRequest.RequestType.FROM_USER
        attrs["request_type"] = request_type

        user = attrs["user"]
        barrier = attrs["barrier"]

        if not barrier.is_active:
            raise NotFound("Barrier not found.")
        if not user.is_active:
            raise NotFound("User not found.")

        if request_type == AccessRequest.RequestType.FROM_USER:
            if user != current_user:
                raise PermissionDenied("You cannot create access request for other user.")
            if not barrier.is_public:
                raise NotFound("Barrier not found.")
        else:
            if barrier.owner != current_user:
                raise PermissionDenied("You do not have access to this barrier.")

        # Check for existing pending request
        if AccessRequest.objects.filter(user=user, barrier=barrier, status=AccessRequest.Status.PENDING).exists():
            raise ConflictError("An active access request already exists for this user and barrier.")

        # Check if user already has access
        if UserBarrier.objects.filter(user=user, barrier=barrier, is_active=True).exists():
            raise ConflictError("This user already has access to the barrier.")

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
            raise serializers.ValidationError(
                {"status": f"Invalid status transition: '{current_status}' -> '{new_status}'."}
            )

        if new_status == AccessRequest.Status.CANCELLED:
            if (not as_admin and request_type == AccessRequest.RequestType.FROM_BARRIER) or (
                as_admin and request_type == AccessRequest.RequestType.FROM_USER
            ):
                raise PermissionDenied("You are not allowed to cancel this request.")

        if new_status in {AccessRequest.Status.ACCEPTED, AccessRequest.Status.REJECTED}:
            if (not as_admin and request_type == AccessRequest.RequestType.FROM_USER) or (
                as_admin and request_type == AccessRequest.RequestType.FROM_BARRIER
            ):
                raise PermissionDenied("You are not allowed to accept or reject this request.")

        if "hidden_for_admin" in attrs and not as_admin:
            raise serializers.ValidationError({"hidden_for_admin": "Only admins can modify field 'hidden_for_admin'."})
        if "hidden_for_user" in attrs and as_admin:
            raise serializers.ValidationError({"hidden_for_user": "Only users can modify field 'hidden_for_user'."})

        return attrs
