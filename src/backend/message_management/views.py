from datetime import timedelta

from django.http import Http404
from django.utils.dateparse import parse_datetime
from django.utils.timezone import localtime, now
from rest_framework.decorators import permission_classes
from rest_framework.exceptions import NotFound, PermissionDenied, Throttled
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from barriers.models import Barrier, UserBarrier
from core.pagination import BasePaginatedListView
from message_management.models import SMSMessage
from message_management.serializers import SMSMessageSerializer
from message_management.services import SMSService
from phones.models import BarrierPhone


def get_barrier(user, barrier_id, as_admin):
    try:
        barrier = Barrier.objects.get(id=barrier_id)
    except Barrier.DoesNotExist:
        raise NotFound("Barrier not found.")

    if as_admin and barrier.owner != user:
        raise PermissionDenied("You do not have access to this barrier.")
    if not as_admin and not UserBarrier.user_has_access_to_barrier(user, barrier):
        raise PermissionDenied("You do not have access to this barrier.")

    return barrier


class BaseSMSMessageListView(BasePaginatedListView):
    serializer_class = SMSMessageSerializer
    pagination_response_key = "sms"

    DEFAULT_ORDERING = ["-updated_at"]
    ALLOWED_ORDERING_FIELDS = {
        "message_type",
        "phone_command_type",
        "status",
        "sent_at",
        "updated_at",
        "log__phone",
        "log__created_at",
    }

    lookup_field = "id"

    as_admin = False

    def get_queryset(self):
        user = self.request.user
        barrier = get_barrier(user, self.kwargs["id"], self.as_admin)

        ordering = self.request.query_params.get("ordering", "").strip()
        ordering_fields = [f.strip() for f in ordering.split(",") if f.strip()]
        safe_ordering = [f for f in ordering_fields if f.lstrip("-") in self.ALLOWED_ORDERING_FIELDS]
        if not safe_ordering:
            safe_ordering = self.DEFAULT_ORDERING

        queryset = SMSMessage.objects.filter(log__barrier=barrier).exclude(
            message_type=SMSMessage.MessageType.VERIFICATION_CODE
        )

        if not self.as_admin:
            queryset = queryset.filter(log__phone__user=user, message_type=SMSMessage.MessageType.PHONE_COMMAND)

        phone_id = self.request.query_params.get("phone", "").strip()
        if phone_id and phone_id.isdigit():
            queryset = queryset.filter(log__phone_id=int(phone_id))

        log_id = self.request.query_params.get("log", "").strip()
        if log_id and log_id.isdigit():
            queryset = queryset.filter(log_id=log_id)

        message_type = self.request.query_params.get("message_type", "").strip()
        if message_type:
            queryset = queryset.filter(message_type=message_type)

        phone_command_type = self.request.query_params.get("phone_command_type", "").strip()
        if phone_command_type:
            queryset = queryset.filter(phone_command_type=phone_command_type)

        status = self.request.query_params.get("status", "").strip()
        if status:
            queryset = queryset.filter(status=status)

        sent_from = self.request.query_params.get("sent_from", "").strip()
        if sent_from:
            dt = parse_datetime(sent_from)
            if dt:
                queryset = queryset.filter(sent_at__gte=dt)

        sent_to = self.request.query_params.get("sent_to", "").strip()
        if sent_to:
            dt = parse_datetime(sent_to)
            if dt:
                queryset = queryset.filter(sent_at__lte=dt)

        updated_from = self.request.query_params.get("updated_from", "").strip()
        if updated_from:
            dt = parse_datetime(updated_from)
            if dt:
                queryset = queryset.filter(updated_at__gte=dt)

        updated_to = self.request.query_params.get("updated_to", "").strip()
        if updated_to:
            dt = parse_datetime(updated_to)
            if dt:
                queryset = queryset.filter(updated_at__lte=dt)

        return queryset.order_by(*safe_ordering)


class UserSMSMessageListView(BaseSMSMessageListView):
    as_admin = False


@permission_classes([IsAdminUser])
class AdminSMSMessageListView(BaseSMSMessageListView):
    as_admin = True


class BaseSMSMessageDetailView(RetrieveAPIView):
    serializer_class = SMSMessageSerializer
    lookup_field = "id"
    as_admin = False

    def get_queryset(self):
        return SMSMessage.objects.all()

    def get_object(self):
        try:
            sms = super().get_object()
        except Http404:
            raise NotFound("Sms message not found.")
        user = self.request.user
        log = sms.log

        if not log:
            raise NotFound("You do not have access to this SMS.")

        barrier = log.barrier
        phone = log.phone

        if self.as_admin and barrier.owner != user:
            raise PermissionDenied("You do not have access to this SMS.")
        if not self.as_admin:
            if not phone or phone.user != user:
                raise PermissionDenied("You do not have access to this SMS.")
            if sms.message_type == SMSMessage.MessageType.BARRIER_SETTING:
                raise PermissionDenied("You do not have access to this SMS.")

        return sms


class UserSMSMessageDetailView(BaseSMSMessageDetailView):
    as_admin = False


@permission_classes([IsAdminUser])
class AdminSMSMessageDetailView(BaseSMSMessageDetailView):
    as_admin = True


class BaseSMSMessageRetryView(APIView):
    as_admin = False
    MAX_AGE_DAYS = 2

    def get_object(self, id, user):
        try:
            sms = SMSMessage.objects.get(id=id)
        except SMSMessage.DoesNotExist:
            raise NotFound("Sms message not found.")

        if sms.message_type in [SMSMessage.MessageType.VERIFICATION_CODE, SMSMessage.MessageType.BALANCE_CHECK]:
            raise PermissionDenied("Cannot retry this message.")

        log = sms.log
        if not log:
            raise PermissionDenied("Cannot retry this message.")

        barrier = log.barrier
        phone = log.phone

        if self.as_admin:
            if barrier.owner != user:
                raise PermissionDenied("You do not have access to this SMS.")
        else:
            if sms.message_type == SMSMessage.MessageType.BARRIER_SETTING:
                raise PermissionDenied("You do not have access to this SMS.")
            if not phone or phone.user != user:
                raise PermissionDenied("You do not have access to this SMS.")

        if sms.status != SMSMessage.Status.FAILED:
            raise PermissionDenied("Only failed messages can be retried.")

        if now() - sms.sent_at > timedelta(days=self.MAX_AGE_DAYS):
            raise PermissionDenied("Message is too old to retry.")

        recent_sms = (
            SMSMessage.objects.filter(log=log, sent_at__gte=now() - timedelta(minutes=10))
            .exclude(id=sms.id)
            .order_by("-sent_at")
            .first()
        )

        if recent_sms:
            retry_after = int((recent_sms.sent_at + timedelta(minutes=10) - now()).total_seconds())
            raise Throttled(wait=retry_after, detail="Another SMS was already sent recently for this action.")

        return sms, phone, log

    def post(self, request, id):
        sms, phone, log = self.get_object(id, request.user)

        if sms.message_type == SMSMessage.MessageType.PHONE_COMMAND:
            command = sms.phone_command_type
            phone_type = phone.type
            now_dt = localtime(now())

            if phone_type in [BarrierPhone.PhoneType.TEMPORARY, BarrierPhone.PhoneType.SCHEDULE]:
                from scheduler.task_manager import PhoneTaskManager

                in_interval = PhoneTaskManager(phone, log).is_in_active_interval(now_dt)

                if in_interval and command == SMSMessage.PhoneCommandType.CLOSE:
                    raise PermissionDenied("Cannot retry this message.")
                if not in_interval and command == SMSMessage.PhoneCommandType.OPEN:
                    raise PermissionDenied("Cannot retry this message.")

        new_sms = SMSService.retry_sms(sms)
        return Response({"message": "SMS resent successfully.", "new_sms_id": new_sms.id})


class UserSMSMessageRetryView(BaseSMSMessageRetryView):
    as_admin = False


@permission_classes([IsAdminUser])
class AdminSMSMessageRetryView(BaseSMSMessageRetryView):
    as_admin = True
