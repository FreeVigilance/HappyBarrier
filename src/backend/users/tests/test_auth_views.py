import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from conftest import ADMIN_PASSWORD, OTHER_PHONE
from users.models import User
from verifications.models import Verification


@pytest.mark.django_db
class TestAdminPasswordVerificationView:
    """Tests for AdminPasswordVerificationView"""

    url = reverse("admin_password_verification")

    def test_valid_admin_credentials_returns_success(self, api_client, admin_user):
        """Test verifying admin password"""

        response = api_client.post(
            self.url,
            {"phone": admin_user.phone, "password": ADMIN_PASSWORD},
        )

        assert response.status_code == status.HTTP_200_OK

    def test_admin_password_verification_invalid(self, api_client, admin_user):
        """Test verifying an incorrect admin password"""

        response = api_client.post(self.url, {"phone": admin_user.phone, "password": "wrongpassword"})
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestLoginView:
    """Tests for LoginView"""

    url = reverse("login")

    def test_valid_login_returns_success(self, api_client, verified_verification, user):
        """Test successful login"""

        response = api_client.post(
            self.url, {"phone": user.phone, "verification_token": verified_verification.verification_token}
        )

        assert response.status_code == status.HTTP_200_OK
        verified_verification.refresh_from_db()
        assert verified_verification.status == Verification.Status.USED
        assert "access_token" in response.data
        assert "refresh_token" in response.data
        db_user = User.objects.get_by_phone(user.phone)
        assert db_user.is_active is True
        assert db_user.last_login is not None

    def test_login_unverified_code(self, api_client, login_verification):
        """Test login with unverified code"""

        response = api_client.post(
            self.url,
            {"phone": login_verification.phone, "verification_token": login_verification.verification_token},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_blocked_user(self, api_client, create_verification, blocked_user):
        """Test login with blocked user"""

        verification = create_verification(
            phone=blocked_user.phone, mode=Verification.Mode.LOGIN, status=Verification.Status.VERIFIED
        )

        response = api_client.post(
            self.url,
            {"phone": blocked_user.phone, "verification_token": verification.verification_token},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestCheckAdminView:
    """Tests for CheckAdminView"""

    url = reverse("check_admin")

    def test_check_admin_success(self, api_client, admin_user):
        """Test checking if an admin user is recognized correctly"""

        response = api_client.post(self.url, {"phone": admin_user.phone})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_admin"] is True

    def test_check_non_admin_success(self, api_client, user):
        """Test checking if a regular user is not an admin"""

        response = api_client.post(self.url, {"phone": user.phone})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_admin"] is False

    def test_check_non_existing_user(self, api_client):
        """Test checking a non-existing user returns is_admin: false"""

        response = api_client.post(self.url, {"phone": OTHER_PHONE})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_admin"] is False

    def test_check_admin_missing_phone(self, api_client):
        """Test checking admin status without providing a phone number"""

        response = api_client.post(self.url, {})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {"phone": ["This field is required."]}


@pytest.mark.django_db
class TestTokenRefreshView:
    """Tests for TokenRefreshView"""

    def test_token_refresh(self, api_client, user):
        """Test refreshing JWT token"""

        refresh = RefreshToken.for_user(user)
        response = api_client.post(reverse("token_refresh"), {"refresh": str(refresh)})

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data


@pytest.mark.django_db
class TestResetPasswordView:
    """Tests for ResetPasswordView"""

    url = reverse("admin_reset_password")

    def test_reset_password_success(self, api_client, admin_user, reset_verification):
        """Test resetting password successfully"""

        response = api_client.patch(
            self.url,
            {
                "phone": admin_user.phone,
                "new_password": "NewSecurePass!",
                "verification_token": reset_verification.verification_token,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        admin_user.refresh_from_db()
        assert admin_user.check_password("NewSecurePass!") is True

        reset_verification.refresh_from_db()
        assert reset_verification.status == Verification.Status.USED

    def test_reset_password_blocked_user(self, api_client, admin_user, reset_verification):
        """Test that blocked admin cannot reset password"""

        admin_user.is_active = False
        admin_user.save()

        response = api_client.patch(
            self.url,
            {
                "phone": admin_user.phone,
                "new_password": "BlockedUserPass!",
                "verification_token": reset_verification.verification_token,
            },
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["error"] == "User is blocked."
