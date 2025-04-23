import logging

from rest_framework import generics
from rest_framework.decorators import permission_classes
from rest_framework.exceptions import MethodNotAllowed, PermissionDenied
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import IsAdminUser

from access_requests.models import AccessRequest
from access_requests.serializers import (
    AccessRequestSerializer,
    CreateAccessRequestSerializer,
    UpdateAccessRequestSerializer,
)
from barriers.models import UserBarrier
from core.pagination import BasePaginatedListView
from core.utils import created_response, success_response

logger = logging.getLogger(__name__)


class BaseCreateAccessRequestView(generics.CreateAPIView):
    """Base view for creating access requests"""

    queryset = AccessRequest.objects.all()
    serializer_class = CreateAccessRequestSerializer
    as_admin = False

    def get_serializer_context(self):
        """Pass request to serializer for access to current user."""

        context = super().get_serializer_context()
        context["request"] = self.request
        context["as_admin"] = self.as_admin
        return context

    def create(self, request, *args, **kwargs):
        """Handle access request creation and return proper response."""

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        # TODO - send an sms with invitation to users

        response_serializer = AccessRequestSerializer(serializer.instance, context=self.get_serializer_context())
        return created_response(response_serializer.data)


class CreateAccessRequestView(BaseCreateAccessRequestView):
    """Create a new access request (by user)."""

    as_admin = False


@permission_classes([IsAdminUser])
class AdminCreateAccessRequestView(BaseCreateAccessRequestView):
    """Create a new access request (by admin)."""

    as_admin = True


class BaseAccessRequestListView(BasePaginatedListView):
    """Base view for listing access requests with filtering and sorting"""

    as_admin = False
    serializer_class = AccessRequestSerializer
    pagination_response_key = "access_requests"

    DEFAULT_ORDERING = "-created_at"
    ALLOWED_ORDERING_FIELDS = {"created_at", "finished_at", "status"}

    def get_serializer_context(self):
        """Pass request to serializer for access to current user."""

        context = super().get_serializer_context()
        context["request"] = self.request
        context["as_admin"] = self.as_admin
        return context

    def get_base_queryset(self):
        """To be implemented in subclasses"""

        raise NotImplementedError

    def get_queryset(self):
        request = self.request

        ordering = request.query_params.get("ordering", self.DEFAULT_ORDERING)
        if ordering.lstrip("-") not in self.ALLOWED_ORDERING_FIELDS:
            ordering = self.DEFAULT_ORDERING

        queryset = self.get_base_queryset()

        # Filter by status
        status_value = request.query_params.get("status")
        if status_value and status_value in AccessRequest.Status.values:
            queryset = queryset.filter(status=status_value)

        # Filter by barrier
        barrier_id = request.query_params.get("barrier_id")
        if barrier_id and barrier_id.isdigit():
            queryset = queryset.filter(barrier_id=int(barrier_id))

        # Filter by hidden flag
        hidden_bool = request.query_params.get("hidden", "false").lower() == "true"
        hidden_field = "hidden_for_admin" if self.as_admin else "hidden_for_user"
        queryset = queryset.filter(**{hidden_field: hidden_bool})

        # Filter by type: incoming / outgoing
        type = request.query_params.get("type")
        if type == "incoming" and self.as_admin or type == "outgoing" and not self.as_admin:
            queryset = queryset.filter(request_type=AccessRequest.RequestType.FROM_USER)
        elif type == "outgoing" and self.as_admin or type == "incoming" and not self.as_admin:
            queryset = queryset.filter(request_type=AccessRequest.RequestType.FROM_BARRIER)

        # Filter cancelled requests created by someone else
        queryset = queryset.exclude(
            status=AccessRequest.Status.CANCELLED,
            request_type=(
                AccessRequest.RequestType.FROM_USER if self.as_admin else AccessRequest.RequestType.FROM_BARRIER
            ),
        )

        return queryset.order_by(ordering)


class MyAccessRequestsListView(BaseAccessRequestListView):
    """List access requests for the current user"""

    as_admin = False

    def get_base_queryset(self):
        return AccessRequest.objects.filter(user=self.request.user)


@permission_classes([IsAdminUser])
class AdminAccessRequestsListView(BaseAccessRequestListView):
    """List access requests related to admin's barriers"""

    as_admin = True

    def get_base_queryset(self):
        return AccessRequest.objects.filter(barrier__owner=self.request.user)


class BaseAccessRequestView(RetrieveUpdateAPIView):
    """Base view for GET and PATCH on access requests"""

    queryset = AccessRequest.objects.all()
    serializer_class = AccessRequestSerializer
    lookup_field = "id"
    as_admin = False

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["as_admin"] = self.as_admin
        return context

    def get_object(self):
        access_request = super().get_object()
        user = self.request.user

        if self.as_admin and access_request.barrier.owner != user or not self.as_admin and access_request.user != user:
            raise PermissionDenied("You don't have access to this access request.")

        if access_request.status == AccessRequest.Status.CANCELLED and (
            self.as_admin
            and access_request.request_type == AccessRequest.RequestType.FROM_USER
            or not self.as_admin
            and access_request.request_type == AccessRequest.RequestType.FROM_BARRIER
        ):
            raise PermissionDenied("You don't have access to this access request.")

        return access_request

    def patch(self, request, *args, **kwargs):
        access_request = self.get_object()
        serializer = UpdateAccessRequestSerializer(
            access_request, data=request.data, partial=True, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        if access_request.status == AccessRequest.Status.ACCEPTED:
            UserBarrier.create(user=access_request.user, barrier=access_request.barrier, access_request=access_request)

        return success_response(AccessRequestSerializer(access_request, context=self.get_serializer_context()).data)

    def put(self, request, *args, **kwargs):
        raise MethodNotAllowed("PUT")


class AccessRequestView(BaseAccessRequestView):
    """User access request view (get and patch own requests)"""

    as_admin = False


@permission_classes([IsAdminUser])
class AdminAccessRequestView(BaseAccessRequestView):
    """Admin view to access and update requests"""

    as_admin = True
