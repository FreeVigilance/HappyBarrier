import logging

from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.decorators import permission_classes
from rest_framework.exceptions import MethodNotAllowed, NotFound, PermissionDenied
from rest_framework.generics import DestroyAPIView
from rest_framework.permissions import IsAdminUser

from barriers.models import Barrier, BarrierLimit, UserBarrier
from barriers.serializers import BarrierLimitSerializer
from barriers_management.serializers import (
    AdminBarrierSerializer,
    CreateBarrierSerializer,
    UpdateBarrierLimitSerializer,
    UpdateBarrierSerializer,
)
from core.pagination import BasePaginatedListView
from core.utils import created_response, deleted_response, success_response
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
        """Add explicit permission check and better 403 response"""

        barrier = super().get_object()
        if barrier.owner != self.request.user:
            raise PermissionDenied(detail="You do not have permission to access this barrier.")

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
        barrier = super().get_object()

        if barrier.owner != self.request.user:
            raise PermissionDenied("You are not the owner of this barrier.")

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
        barrier = get_object_or_404(Barrier, id=barrier_id, is_active=True)

        if barrier.owner != self.request.user:
            raise PermissionDenied("You are not the owner of this barrier.")

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

        barrier = get_object_or_404(Barrier, id=barrier_id, is_active=True)
        user = get_object_or_404(User, id=user_id, is_active=True)

        if barrier.owner != self.request.user:
            raise PermissionDenied("You are not the owner of this barrier.")

        user_barrier = UserBarrier.objects.filter(user=user, barrier=barrier, is_active=True).first()

        if not user_barrier:
            raise NotFound("User not found in this barrier.")

        return user_barrier

    def delete(self, request, *args, **kwargs):
        user_barrier = self.get_object()
        user_barrier.is_active = False
        user_barrier.save(update_fields=["is_active"])
        return success_response({"message": "User successfully removed from barrier."})
