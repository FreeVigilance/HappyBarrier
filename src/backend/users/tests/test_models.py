import pytest
from rest_framework import status

from conftest import ADMIN_PHONE, BLOCKED_USER_PHONE, OTHER_PHONE, SUPERUSER_PHONE, USER_NAME, USER_PHONE
from users.models import User


@pytest.mark.django_db
class TestUserManager:
    def test_create_user(self, user):
        """Test creating a regular user."""

        assert user.phone == USER_PHONE
        assert user.is_active is True
        assert user.role == User.Role.USER
        assert user.is_staff is False
        assert user.is_superuser is False

    def test_create_admin(self, admin_user):
        """Test creating an admin user."""

        assert admin_user.phone == ADMIN_PHONE
        assert admin_user.is_staff is True
        assert admin_user.role == User.Role.ADMIN
        assert admin_user.is_superuser is False

    def test_create_superuser(self, superuser):
        """Test creating a superuser."""

        assert superuser.phone == SUPERUSER_PHONE
        assert superuser.is_staff is True
        assert superuser.is_superuser is True
        assert superuser.role == User.Role.SUPERUSER

    def test_get_by_phone(self, user):
        """Test retrieving a user by phone using UserManager."""

        found_user = User.objects.get_by_phone(user.phone)
        assert found_user == user

        not_found = User.objects.get_by_phone(OTHER_PHONE)
        assert not_found is None

    def test_check_phone_blocked_returns_none_for_active_user(self, user):
        assert User.objects.check_phone_blocked(USER_PHONE) is None

    def test_check_phone_blocked_returns_error_for_blocked_user(self, blocked_user):
        response = User.objects.check_phone_blocked(BLOCKED_USER_PHONE)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert blocked_user.block_reason in response.data["error"]


@pytest.mark.django_db
class TestUserModel:
    def test_str_method(self, user):
        """Test __str__ method."""

        assert str(user) == f"{USER_PHONE} {USER_NAME}"

    def test_get_full_name(self, user):
        """Test get_full_name method."""

        assert user.get_full_name() == USER_NAME

    def test_get_phone(self, user):
        """Test get_phone method."""

        assert user.get_phone() == USER_PHONE

    def test_get_short_name(self, user):
        """Test get_short_name method."""

        assert user.get_short_name() == USER_PHONE

    def test_delete_raises_permission_denied(self, user):
        """Test that delete() raises PermissionDenied."""

        with pytest.raises(Exception) as exc_info:
            user.delete()
        assert "not allowed" in str(exc_info.value)
