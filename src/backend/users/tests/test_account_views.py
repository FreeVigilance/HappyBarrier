import pytest
from django.urls import reverse
from rest_framework import status

from conftest import ADMIN_PASSWORD, OTHER_PHONE
from users.models import User
from verifications.models import Verification


@pytest.mark.django_db
class TestUserAccountView:
    """Tests for UserAccountView"""

    def test_get_user_profile(self, authenticated_client, user):
        """Test retrieving user profile"""

        response = authenticated_client.get(reverse("user_account"))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["phone"] == user.phone
        assert response.data["full_name"] == user.full_name

    def test_edit_user_profile(self, authenticated_client):
        """Test editing user profile"""

        data = {"full_name": "New Name", "phone_privacy": User.PhonePrivacy.PRIVATE}
        response = authenticated_client.patch(reverse("user_account"), data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["full_name"] == "New Name"
        assert response.data["phone_privacy"] == User.PhonePrivacy.PRIVATE

    def test_delete_user_account(self, authenticated_client, user, delete_verification):
        """Test deleting user account"""

        response = authenticated_client.delete(
            reverse("user_account"),
            {"verification_token": delete_verification.verification_token},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        user.refresh_from_db()
        assert not user.is_active
        delete_verification.refresh_from_db()
        assert delete_verification.status == Verification.Status.USED

    def test_delete_user_account_invalid_verification(self, authenticated_client, create_verification):
        """Test deleting user account with invalid verification token"""
        verification_token = create_verification(mode=Verification.Mode.LOGIN).verification_token

        response = authenticated_client.delete(reverse("user_account"), {"verification_token": verification_token})

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["error"] == "Invalid verification mode."

    def test_put_method_not_allowed(self, authenticated_client):
        """Test that PUT method is not allowed on user account view"""

        response = authenticated_client.put(reverse("user_account"), {})

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert response.data["detail"] == 'Method "PUT" not allowed.'


@pytest.mark.django_db
class TestChangePhoneView:
    """Tests for ChangePhoneView"""

    def test_change_phone_success(self, authenticated_client, user, old_phone_verification, new_phone_verification):
        """Test changing phone number successfully"""

        data = {
            "new_phone": OTHER_PHONE,
            "old_verification_token": old_phone_verification.verification_token,
            "new_verification_token": new_phone_verification.verification_token,
        }
        response = authenticated_client.patch(reverse("change_phone"), data)

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.phone == OTHER_PHONE

        old_phone_verification.refresh_from_db()
        new_phone_verification.refresh_from_db()
        assert old_phone_verification.status == Verification.Status.USED
        assert new_phone_verification.status == Verification.Status.USED


@pytest.mark.django_db
class TestChangePasswordView:
    """Tests for ChangePasswordView"""

    def test_change_password_success(self, authenticated_admin_client, admin_user, password_verification):
        """Test changing password successfully"""

        data = {
            "old_password": ADMIN_PASSWORD,
            "new_password": "NewPass456!",
            "verification_token": password_verification.verification_token,
        }
        response = authenticated_admin_client.patch(reverse("admin_change_password"), data)

        assert response.status_code == status.HTTP_200_OK
        admin_user.refresh_from_db()
        assert admin_user.check_password("NewPass456!") is True

        password_verification.refresh_from_db()
        assert password_verification.status == Verification.Status.USED
