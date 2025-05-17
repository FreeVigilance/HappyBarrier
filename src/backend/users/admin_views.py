from django.http import Http404
from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.decorators import permission_classes
from rest_framework.exceptions import NotFound
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAdminUser
from rest_framework.views import APIView

from core.utils import error_response, success_response
from users.models import User
from users.serializers import SearchUserSerializer, UserSerializer


def admin_block_password_change_view(request):
    """Custom admin view to block password changes via the Django admin panel."""

    return render(request, "admin/password_change.html", status=status.HTTP_403_FORBIDDEN)


@permission_classes([IsAdminUser])
class AdminUserAccountView(generics.RetrieveAPIView):
    """Get user details (for admins only)."""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    lookup_field = "id"

    def get_object(self):
        try:
            return super().get_object()
        except Http404:
            raise NotFound("User not found.")


@permission_classes([IsAdminUser])
class AdminBlockUserView(APIView):
    """Block user (for admins only)."""

    def patch(self, request, id):
        try:
            user = get_object_or_404(User, id=id)
        except Http404:
            return error_response("User not found.", status.HTTP_404_NOT_FOUND)

        reason = request.data.get("reason")
        if not reason:
            return error_response("Reason is required for blocking a user.", status.HTTP_400_BAD_REQUEST)

        if user.role != User.Role.USER:
            return error_response("You cannot block an admin.", status.HTTP_403_FORBIDDEN)

        if not user.is_active:
            return error_response("User is already blocked.", status.HTTP_400_BAD_REQUEST)

        user.block_reason = reason
        user.is_active = False
        user.save(update_fields=["is_active", "block_reason"])

        return success_response(UserSerializer(user).data)


@permission_classes([IsAdminUser])
class AdminUnblockUserView(APIView):
    """Unblock a user (for admins only)."""

    def patch(self, request, id):
        try:
            user = get_object_or_404(User, id=id)
        except Http404:
            return error_response("User not found.", status.HTTP_404_NOT_FOUND)

        if user.is_active:
            return error_response("User is already active.", status.HTTP_400_BAD_REQUEST)

        if user.role != User.Role.USER:
            return error_response("You cannot unblock an admin.", status.HTTP_403_FORBIDDEN)

        user.block_reason = ""
        user.is_active = True
        user.save()

        return success_response(UserSerializer(user).data)


@permission_classes([IsAdminUser])
class AdminSearchUserView(APIView):
    """Search user by given phone number (for admins only)."""

    def post(self, request):
        serializer = SearchUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data["phone"]
        user = User.objects.get_by_phone(phone)

        if not user:
            return error_response("User not found.", status.HTTP_404_NOT_FOUND)

        return success_response(UserSerializer(user).data)
