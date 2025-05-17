from django.http import Http404
from django.utils.dateparse import parse_datetime
from rest_framework.decorators import permission_classes
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.generics import RetrieveAPIView, get_object_or_404
from rest_framework.permissions import IsAdminUser, IsAuthenticated

from action_history.serializers import BarrierActionLogSerializer
from barriers.models import Barrier, UserBarrier
from core.pagination import BasePaginatedListView
from message_management.models import BarrierActionLog
from users.models import User


def get_barrier(user, barrier_id, as_admin):
    try:
        barrier = get_object_or_404(Barrier, id=barrier_id)
    except Http404:
        raise NotFound("Barrier not found.")

    if as_admin and barrier.owner != user:
        raise PermissionDenied("You do not have access to this barrier.")
    if not as_admin and not UserBarrier.user_has_access_to_barrier(user, barrier):
        raise PermissionDenied("You do not have access to this barrier.")

    return barrier


class BaseBarrierActionLogListView(BasePaginatedListView):
    """Base view for listing log of actions with phones in barrier with filtering and sorting for user or admin"""

    serializer_class = BarrierActionLogSerializer
    pagination_response_key = "actions"

    DEFAULT_ORDERING = ["barrier__address", "phone__phone", "-created_at"]
    ALLOWED_ORDERING_FIELDS = {"barrier__address", "phone__phone", "phone__type", "author", "action_type", "created_at"}

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

        queryset = BarrierActionLog.objects.filter(barrier=barrier)

        if self.as_admin:
            user_id = self.request.query_params.get("user", "").strip()
            if user_id:
                if not User.objects.filter(id=user_id, is_active=True).exists():
                    raise NotFound("User not found.")
                queryset = queryset.filter(phone__user_id=user_id)
        else:
            queryset = queryset.filter(phone__user=user)

        phone_id = self.request.query_params.get("phone", "").strip()
        if phone_id and phone_id.isdigit():
            queryset = queryset.filter(phone_id=int(phone_id))

        author = self.request.query_params.get("author", "").strip()
        if author in BarrierActionLog.Author.values:
            queryset = queryset.filter(author=author)

        action_type = self.request.query_params.get("action_type", "").strip()
        if action_type in BarrierActionLog.ActionType.values:
            queryset = queryset.filter(action_type=action_type)

        reason = self.request.query_params.get("reason", "").strip()
        if reason in BarrierActionLog.Reason.values:
            queryset = queryset.filter(reason=reason)

        created_from = self.request.query_params.get("created_from", "").strip()
        created_to = self.request.query_params.get("created_to", "").strip()

        if created_from:
            dt = parse_datetime(created_from)
            if dt:
                queryset = queryset.filter(created_at__gte=dt)

        if created_to:
            dt = parse_datetime(created_to)
            if dt:
                queryset = queryset.filter(created_at__lte=dt)

        return queryset.order_by(*safe_ordering)


class UserBarrierActionLogListView(BaseBarrierActionLogListView):
    """List of logs of actions for user in a barrier"""

    as_admin = False


@permission_classes([IsAdminUser])
class AdminBarrierActionLogListView(BaseBarrierActionLogListView):
    """List of logs of actions of any user in admin's barrier"""

    as_admin = True


@permission_classes([IsAuthenticated])
class BaseBarrierActionLogDetailView(RetrieveAPIView):
    serializer_class = BarrierActionLogSerializer
    lookup_field = "id"

    as_admin = False

    def get_queryset(self):
        return BarrierActionLog.objects.all()

    def get_object(self):
        try:
            action_log = super().get_object()
        except Http404:
            raise NotFound("Barrier log not found.")
        user = self.request.user
        barrier = action_log.barrier
        phone = action_log.phone

        if self.as_admin and barrier.owner != user:
            raise PermissionDenied("You do not have access to this log entry.")
        if not self.as_admin and not UserBarrier.user_has_access_to_barrier(user, barrier):
            raise PermissionDenied("You do not have access to this log entry.")
        if not self.as_admin and (phone is None or phone.user != user):
            raise PermissionDenied("You do not have access to this log entry.")

        return action_log


class UserBarrierActionLogDetailView(BaseBarrierActionLogDetailView):
    """Get action log record by user"""

    as_admin = False


@permission_classes([IsAdminUser])
class AdminBarrierActionLogDetailView(BaseBarrierActionLogDetailView):
    """Get action log record by admin"""

    as_admin = True
