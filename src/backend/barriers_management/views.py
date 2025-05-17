import logging
from datetime import timedelta

from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from rest_framework import generics, status
from rest_framework.decorators import permission_classes
from rest_framework.exceptions import APIException, MethodNotAllowed, NotFound, PermissionDenied, ValidationError
from rest_framework.generics import DestroyAPIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from access_requests.models import AccessRequest
from action_history.models import BarrierActionLog
from barriers.models import Barrier, BarrierLimit, UserBarrier
from barriers.serializers import BarrierLimitSerializer
from barriers_management.serializers import (
    AdminBarrierSerializer,
    BarrierSettingsSerializer,
    CreateBarrierSerializer,
    SendBarrierSettingSerializer,
    UpdateBarrierLimitSerializer,
    UpdateBarrierSerializer,
)
from core.pagination import BasePaginatedListView
from core.utils import created_response, deleted_response, success_response
from message_management.models import SMSMessage
from message_management.services import SMSService
from phones.models import BarrierPhone
from users.models import User
from users.serializers import UserSerializer

logger = logging.getLogger(__name__)


@permission_classes([IsAdminUser])
class CreateBarrierView(generics.CreateAPIView):
    """Create a new barrier (admin only)."""

    queryset = Barrier.objects.all()
    serializer_class = CreateBarrierSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def perform_create(self, serializer):
        barrier = serializer.save()
        BarrierLimit.objects.create(barrier=barrier)

        # Adding admin into barrier
        access_request = AccessRequest.objects.create(
            user=self.request.user,
            barrier=barrier,
            request_type=AccessRequest.RequestType.FROM_BARRIER,
            status=AccessRequest.Status.ACCEPTED,
            finished_at=now(),
        )

        UserBarrier.create(
            user=self.request.user,
            barrier=barrier,
            access_request=access_request,
        )

        phone, log = BarrierPhone.create(
            user=self.request.user,
            barrier=barrier,
            phone=self.request.user.phone,
            type=BarrierPhone.PhoneType.PRIMARY,
            name=self.request.user.full_name,
            author=BarrierActionLog.Author.SYSTEM,
            reason=BarrierActionLog.Reason.ACCESS_GRANTED,
        )
        phone.send_sms_to_create(log)

    def create(self, request, *args, **kwargs):
        """Use a different serializer for the response"""

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        response_serializer = AdminBarrierSerializer(serializer.instance, context=self.get_serializer_context())
        return created_response(response_serializer.data)


@permission_classes([IsAdminUser])
class MyAdminBarrierListView(BasePaginatedListView):
    """Get a list of barriers managed by the current admin"""

    serializer_class = AdminBarrierSerializer
    pagination_response_key = "barriers"

    ALLOWED_ORDERING_FIELDS = {"address", "created_at", "updated_at"}
    DEFAULT_ORDERING = "address"

    def get_queryset(self):
        """
        Use the `ordering` query parameter to sort results.
        Prefix with `-` for descending order (e.g., ?ordering=-created_at for newest first),
        or use the field name directly for ascending order (e.g., ?ordering=created_at for oldest first).
        """

        ordering = self.request.query_params.get("ordering", self.DEFAULT_ORDERING)
        if ordering.lstrip("-") not in self.ALLOWED_ORDERING_FIELDS:
            ordering = self.DEFAULT_ORDERING

        queryset = Barrier.objects.filter(owner=self.request.user, is_active=True)

        return queryset.order_by(ordering)


@permission_classes([IsAdminUser])
class AdminBarrierView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a barrier by ID (admin only)."""

    queryset = Barrier.objects.filter(is_active=True)
    lookup_field = "id"

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return UpdateBarrierSerializer
        return AdminBarrierSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def get_object(self):
        try:
            barrier = super().get_object()
        except Http404:
            raise NotFound("Barrier not found.")

        if barrier.owner != self.request.user:
            raise PermissionDenied("You do not have access to this barrier.")

        return barrier

    def patch(self, request, *args, **kwargs):
        """Update barrier fields (partial update)"""

        barrier = self.get_object()
        serializer = self.get_serializer(barrier, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(AdminBarrierSerializer(barrier).data)

    def delete(self, request, *args, **kwargs):
        """Mark the barrier as inactive (soft delete)"""

        barrier = self.get_object()

        logger.info(f"Deleting user barrier relations on '{barrier.id}' while deleting barrier")
        UserBarrier.objects.filter(barrier=barrier, is_active=True).update(is_active=False)

        phones = BarrierPhone.objects.filter(barrier=barrier, is_active=True)
        for phone in phones:
            _, log = phone.remove(author=BarrierActionLog.Author.ADMIN, reason=BarrierActionLog.Reason.BARRIER_DELETED)
            phone.send_sms_to_delete(log)
            logger.info(
                f"Deleted phone '{phone.phone}' for user '{phone.user.id}' on barrier '{barrier.id}' "
                f"while deleting barrier"
            )

        barrier.is_active = False
        barrier.save(update_fields=["is_active"])
        return deleted_response()

    def put(self, request, *args, **kwargs):
        raise MethodNotAllowed("PUT")


@permission_classes([IsAdminUser])
class AdminBarrierLimitUpdateView(generics.UpdateAPIView):
    """Update or create limits for a barrier (admins only)"""

    serializer_class = UpdateBarrierLimitSerializer
    queryset = Barrier.objects.filter(is_active=True)
    lookup_field = "id"

    def get_object(self):
        try:
            barrier = super().get_object()
        except Http404:
            raise NotFound("Barrier not found.")

        if barrier.owner != self.request.user:
            raise PermissionDenied("You do not have access to this barrier.")

        limit, _ = BarrierLimit.objects.get_or_create(barrier=barrier)
        return limit

    def patch(self, request, *args, **kwargs):
        limit = self.get_object()
        serializer = self.get_serializer(limit, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return success_response(BarrierLimitSerializer(limit).data)

    def put(self, request, *args, **kwargs):
        raise MethodNotAllowed("PUT")


@permission_classes([IsAdminUser])
class AdminBarrierUsersListView(BasePaginatedListView):
    serializer_class = UserSerializer
    pagination_response_key = "users"

    ALLOWED_ORDERING_FIELDS = {"full_name", "phone"}
    DEFAULT_ORDERING = "full_name"

    lookup_field = "id"

    def get_object(self):
        barrier_id = self.kwargs.get("id")
        try:
            barrier = get_object_or_404(Barrier, id=barrier_id, is_active=True)
        except Http404:
            raise NotFound("Barrier not found.")

        if barrier.owner != self.request.user:
            raise PermissionDenied("You do not have access to this barrier.")

        return barrier

    def get_queryset(self):
        barrier = self.get_object()

        ordering = self.request.query_params.get("ordering", self.DEFAULT_ORDERING)
        if ordering.lstrip("-") not in self.ALLOWED_ORDERING_FIELDS:
            ordering = self.DEFAULT_ORDERING

        return User.objects.filter(
            is_active=True,
            barriers_access__barrier=barrier,
            barriers_access__is_active=True,
        ).order_by(ordering)


@permission_classes([IsAdminUser])
class AdminRemoveUserFromBarrierView(DestroyAPIView):
    def get_object(self):
        barrier_id = self.kwargs["barrier_id"]
        user_id = self.kwargs["user_id"]

        try:
            barrier = get_object_or_404(Barrier, id=barrier_id, is_active=True)
        except Http404:
            raise NotFound("Barrier not found.")
        try:
            user = get_object_or_404(User, id=user_id, is_active=True)
        except Http404:
            raise NotFound("User not found.")

        if barrier.owner != self.request.user:
            raise PermissionDenied("You do not have access to this barrier.")

        user_barrier = UserBarrier.objects.filter(user=user, barrier=barrier, is_active=True).first()

        if not user_barrier:
            raise NotFound("User not found in this barrier.")

        return user_barrier

    def delete(self, request, *args, **kwargs):
        user_barrier = self.get_object()
        user_barrier.is_active = False
        user_barrier.save(update_fields=["is_active"])
        user = user_barrier.user
        barrier = user_barrier.barrier

        logger.info(f"Deleting all phones for user '{user.id}' while leaving barrier '{barrier.id}'")
        phones = BarrierPhone.objects.filter(user=user, barrier=barrier, is_active=True)
        for phone in phones:
            _, log = phone.remove(author=BarrierActionLog.Author.ADMIN, reason=BarrierActionLog.Reason.BARRIER_EXIT)
            phone.send_sms_to_delete(log)

        return success_response({"message": "User successfully removed from barrier."})


@permission_classes([IsAdminUser])
class AdminBarrierSettingsView(APIView):
    def get_barrier(self, barrier_id):
        try:
            barrier = get_object_or_404(Barrier, id=barrier_id, is_active=True)
        except Http404:
            raise NotFound("Barrier not found.")

        if barrier.owner != self.request.user:
            raise PermissionDenied("You do not have access to this barrier.")
        return barrier

    def get(self, request, id):
        barrier = self.get_barrier(id)

        data = SMSService.get_available_barrier_settings(barrier)
        serializer = BarrierSettingsSerializer(data=data)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError:
            raise APIException(
                f"Invalid settings configuration for device model '{barrier.device_model}'. "
                "Please check the server config format."
            )
        return Response(serializer.data)

    def post(self, request, id):
        barrier = self.get_barrier(id)

        serializer = SendBarrierSettingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        setting_key = serializer.validated_data["setting"]
        params = serializer.validated_data["params"]

        log = BarrierActionLog.objects.create(
            barrier=barrier,
            phone=None,
            author=BarrierActionLog.Author.ADMIN,
            action_type=BarrierActionLog.ActionType.BARRIER_SETTING,
            old_value=None,
        )

        SMSService.send_barrier_setting(barrier, setting_key, params, log)

        return Response({"message": "Setting sent successfully.", "action": log.id})


@permission_classes([IsAdminUser])
class AdminSendBalanceCheckView(APIView):
    def post(self, request):
        recent_sms = (
            SMSMessage.objects.filter(message_type=SMSMessage.MessageType.BALANCE_CHECK).order_by("-sent_at").first()
        )

        if recent_sms and now() - recent_sms.sent_at < timedelta(minutes=5):
            retry_after = int((timedelta(minutes=5) - (now() - recent_sms.sent_at)).total_seconds())

            return Response(
                {
                    "detail": "Balance check was already requested recently. Try again later.",
                    "retry_after_seconds": retry_after,
                    "last_sms": {
                        "id": recent_sms.id,
                        "sent_at": recent_sms.sent_at.isoformat(),
                        "status": recent_sms.status,
                    },
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        SMSService.send_balance_check()
        return Response({"message": "Balance check command sent."}, status=status.HTTP_200_OK)
