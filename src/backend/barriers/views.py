import logging

from django.db.models import Q
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.generics import DestroyAPIView, RetrieveAPIView
from rest_framework.views import APIView

from barriers.models import Barrier, BarrierLimit, UserBarrier
from barriers.serializers import BarrierLimitSerializer, BarrierSerializer
from core.pagination import BasePaginatedListView
from core.utils import error_response, success_response

logger = logging.getLogger(__name__)


class ListBarriersView(BasePaginatedListView):
    """List all public barriers with search by address, ordering, pagination"""

    serializer_class = BarrierSerializer
    pagination_response_key = "barriers"

    ALLOWED_ORDERING_FIELDS = {"address"}
    DEFAULT_ORDERING = "address"

    def get_queryset(self):
        """Use the `ordering` query parameter to sort results."""

        ordering = self.request.query_params.get("ordering", self.DEFAULT_ORDERING)
        if ordering.lstrip("-") not in self.ALLOWED_ORDERING_FIELDS:
            ordering = self.DEFAULT_ORDERING

        queryset = Barrier.objects.filter(is_public=True, is_active=True)
        address = self.request.query_params.get("address", "").strip()
        if address:
            queryset = queryset.filter(Q(address__icontains=address.lower()))

        return queryset.order_by(ordering)


class MyBarriersListView(BasePaginatedListView):
    """Retrieve a list of barriers accessible by the current user"""

    serializer_class = BarrierSerializer
    pagination_response_key = "barriers"

    ALLOWED_ORDERING_FIELDS = {"address"}
    DEFAULT_ORDERING = "address"

    def get_queryset(self):
        """Use the `ordering` query parameter to sort results."""

        ordering = self.request.query_params.get("ordering", self.DEFAULT_ORDERING)
        if ordering.lstrip("-") not in self.ALLOWED_ORDERING_FIELDS:
            ordering = self.DEFAULT_ORDERING

        queryset = Barrier.objects.filter(
            users_access__user=self.request.user, users_access__is_active=True, is_active=True
        )

        return queryset.order_by(ordering)


class BarrierView(RetrieveAPIView):
    """
    Retrieve detailed information about a single barrier by ID.
    Accessible only if the barrier is public or the user has access.
    """

    serializer_class = BarrierSerializer
    queryset = Barrier.objects.filter(is_active=True)
    lookup_field = "id"

    def get_object(self):
        barrier = super().get_object()
        user = self.request.user

        if barrier.is_public or (UserBarrier.user_has_access_to_barrier(user, barrier)):
            return barrier

        raise PermissionDenied("You do not have access to this barrier.")


class BarrierLimitView(RetrieveAPIView):
    """Retrieve limits for a specific barrier (for all authenticated users)"""

    serializer_class = BarrierLimitSerializer
    queryset = Barrier.objects.filter(is_active=True)
    lookup_field = "id"

    def get_object(self):
        barrier = super().get_object()
        user = self.request.user

        if not (barrier.is_public or UserBarrier.user_has_access_to_barrier(user, barrier) or barrier.owner == user):
            raise PermissionDenied("You do not have access to this barrier.")

        if not hasattr(barrier, "limits") or barrier.limits is None:
            logger.warning(f"BarrierLimit missing for barrier ID '{barrier.id}'. Creating an empty one.")
            BarrierLimit.objects.create(barrier=barrier)

        return barrier.limits

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)


class LeaveBarrierView(DestroyAPIView):
    queryset = Barrier.objects.filter(is_active=True)
    lookup_field = "id"

    def delete(self, request, *args, **kwargs):
        barrier = self.get_object()

        user_barrier = UserBarrier.objects.filter(user=self.request.user, barrier=barrier, is_active=True).first()
        if not user_barrier:
            return error_response("You do not have access to this barrier.", status.HTTP_403_FORBIDDEN)

        user_barrier.is_active = False
        user_barrier.save(update_fields=["is_active"])
        return success_response({"message": "Left the barrier successfully."})


class BarrierAccessCheckView(APIView):
    """Check if current user has access to a specific barrier"""

    def get(self, request, id):
        barrier = Barrier.objects.filter(id=id, is_active=True).first()
        if not barrier:
            raise NotFound("Barrier not found.")

        has_access = UserBarrier.user_has_access_to_barrier(request.user, barrier)

        return success_response({"has_access": has_access})
