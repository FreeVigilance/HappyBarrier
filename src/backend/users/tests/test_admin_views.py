import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestAdminUserAccountView:
    """Tests for AdminUserAccountView"""

    def test_success(self, authenticated_admin_client, user):
        """Test retrieving user details as an admin"""

        response = authenticated_admin_client.get(reverse("admin_get_user", args=[user.id]))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["phone"] == user.phone

    def test_user_not_found(self, authenticated_admin_client):
        """Test retrieving details of a non-existent user"""

        response = authenticated_admin_client.get(reverse("admin_get_user", args=[999999]))

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["detail"] == "User not found."


@pytest.mark.django_db
class TestAdminBlockUserView:
    """Tests for AdminBlockUserView"""

    def test_success(self, authenticated_admin_client, user):
        """Test blocking a user"""

        response = authenticated_admin_client.patch(reverse("admin_block_user", args=[user.id]), {"reason": "Spamming"})

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.is_active is False
        assert user.block_reason == "Spamming"

    def test_user_not_found(self, authenticated_admin_client):
        """Test blocking a non-existent user"""

        response = authenticated_admin_client.patch(reverse("admin_block_user", args=[999999]))

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["detail"] == "User not found."

    def test_missing_reason(self, authenticated_admin_client, user):
        """Test blocking a user without providing a reason"""

        response = authenticated_admin_client.patch(reverse("admin_block_user", args=[user.id]), {})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_already_blocked_user(self, authenticated_admin_client, blocked_user):
        """Test blocking a user who is already blocked"""

        response = authenticated_admin_client.patch(
            reverse("admin_block_user", args=[blocked_user.id]), {"reason": "Multiple violations"}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestAdminUnblockUserView:
    """Tests for AdminUnblockUserView"""

    def test_success(self, authenticated_admin_client, blocked_user):
        """Test unblocking a user"""

        response = authenticated_admin_client.patch(reverse("admin_unblock_user", args=[blocked_user.id]))

        assert response.status_code == status.HTTP_200_OK
        blocked_user.refresh_from_db()
        assert blocked_user.is_active is True

    def test_user_not_found(self, authenticated_admin_client):
        """Test unblocking a non-existent user"""

        response = authenticated_admin_client.patch(reverse("admin_unblock_user", args=[999999]))

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["detail"] == "User not found."

    def test_already_active_user(self, authenticated_admin_client, user):
        """Test trying to unblock a user who is already active"""

        response = authenticated_admin_client.patch(reverse("admin_unblock_user", args=[user.id]))

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unblock_admin_user(self, authenticated_admin_client, another_admin):
        """Test trying to unblock an admin user"""

        another_admin.is_active = False
        another_admin.save()

        response = authenticated_admin_client.patch(reverse("admin_unblock_user", args=[another_admin.id]))

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestAdminSearchUserView:
    """Tests for AdminSearchUserView"""

    def test_admin_search_user_success(self, authenticated_admin_client, user):
        """Test searching for an existing user by phone"""

        response = authenticated_admin_client.post(reverse("admin_search_user"), {"phone": user.phone})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["phone"] == user.phone

    def test_admin_search_user_not_found(self, authenticated_admin_client):
        """Test searching for a non-existent user"""

        response = authenticated_admin_client.post(reverse("admin_search_user"), {"phone": "+79990000000"})

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_admin_search_user_invalid_phone(self, authenticated_admin_client):
        """Test searching with an invalid phone format"""

        response = authenticated_admin_client.post(reverse("admin_search_user"), {"phone": "invalid_phone"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
