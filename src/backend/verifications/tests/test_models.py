from datetime import timedelta

import pytest
from django.utils.timezone import now
from rest_framework import status

from conftest import ADMIN_PHONE, OTHER_PHONE, USER_PHONE
from verifications.constants import (
    DELETION_DAYS,
    EXPIRATION_MINUTES,
    VERIFICATION_CODE_MAX_LENGTH,
    VERIFICATION_CODE_RESEND_DELAY,
    VERIFICATION_TOKEN_MAX_LENGTH,
)
from verifications.models import MAX_FAIL_COUNT, Verification, VerificationService


@pytest.mark.django_db
class TestVerificationService:
    def test_generate_verification_code(self):
        """Test that verification code has the correct format and length."""

        code = VerificationService.generate_verification_code()

        assert isinstance(code, str)
        assert len(code) == VERIFICATION_CODE_MAX_LENGTH
        assert code.isdigit()

    def test_generate_verification_token(self):
        """Test that verification token has the correct format and length."""

        token = VerificationService.generate_verification_token()

        assert isinstance(token, str)
        assert len(token) == VERIFICATION_TOKEN_MAX_LENGTH
        assert token.isalnum()

    def test_create_new_verification(self):
        """Test creation of a new verification entry."""

        mode = Verification.Mode.LOGIN
        new_verification = VerificationService.create_new_verification(USER_PHONE, mode)

        assert all(
            [
                new_verification.phone == USER_PHONE,
                new_verification.mode == mode,
                new_verification.status == Verification.Status.SENT,
                len(new_verification.code) == VERIFICATION_CODE_MAX_LENGTH,
                len(new_verification.verification_token) == VERIFICATION_TOKEN_MAX_LENGTH,
            ]
        )

    class TestClean:
        def test_verifications_older_than_deletion_days_are_deleted(self, verification):
            """Verifications older than DELETION_DAYS are permanently deleted."""

            verification.created_at = now() - timedelta(days=DELETION_DAYS + 1)
            verification.save()

            VerificationService.clean()
            assert Verification.objects.filter(pk=verification.pk).count() == 0

        def test_recent_verifications_remain_unchanged(self, verification):
            """Verifications newer than EXPIRATION_MINUTES are not expired or deleted."""

            verification.created_at = now() - timedelta(minutes=EXPIRATION_MINUTES - 1)
            verification.save()

            VerificationService.clean()
            verification.refresh_from_db()
            assert verification.status == Verification.Status.SENT

        def test_sent_verification_is_marked_as_expired(self, verification):
            """SENT verifications older than EXPIRATION_MINUTES are marked as EXPIRED."""

            verification.created_at = now() - timedelta(minutes=EXPIRATION_MINUTES + 1)
            verification.save()

            VerificationService.clean()
            verification.refresh_from_db()
            assert verification.status == Verification.Status.EXPIRED

        def test_verified_verification_is_marked_as_expired(self, verified_verification):
            """VERIFIED verifications older than EXPIRATION_MINUTES are marked as EXPIRED."""

            verified_verification.created_at = now() - timedelta(minutes=EXPIRATION_MINUTES + 1)
            verified_verification.save()

            VerificationService.clean()
            assert Verification.objects.filter(pk=verified_verification.pk).exists()

    class TestCheckFailLimits:
        def test_returns_none_below_threshold(self, verification):

            assert VerificationService.check_fail_limits(verification.phone) is None

        def test_returns_error_when_exceeds_threshold(self, verification):
            verification.failed_attempts = MAX_FAIL_COUNT
            verification.save()

            response = VerificationService.check_fail_limits(USER_PHONE)
            assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    class TestCheckUnverifiedLimits:
        def test_returns_none_below_threshold(self, verification):
            """Test counting unverified codes (only `sent` status is counted)."""

            assert VerificationService.check_unverified_limits(USER_PHONE) is None

        def test_returns_error_when_exceeds_threshold(self, verification):
            for _ in range(5):  # threshold is 5
                VerificationService.create_new_verification(verification.phone, Verification.Mode.LOGIN)
            response = VerificationService.check_unverified_limits(verification.phone)

            assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    class TestCheckVerificationMode:
        @pytest.mark.parametrize(
            "mode",
            [
                Verification.Mode.LOGIN,
                Verification.Mode.CHANGE_PHONE_NEW,
            ],
        )
        def test_returns_none_when_user_does_not_exist_and_mode_allows_it(self, mode):
            """Should return None for modes that allow missing user"""

            response = VerificationService.check_verification_mode(USER_PHONE, mode)
            assert response is None

        @pytest.mark.parametrize(
            "mode",
            [
                Verification.Mode.RESET_PASSWORD,
                Verification.Mode.CHANGE_PASSWORD,
                Verification.Mode.DELETE_ACCOUNT,
                Verification.Mode.CHANGE_PHONE_OLD,
            ],
        )
        def test_returns_error_when_user_not_found_for_reset_password(self, mode):
            """Should return 404 if user not found for modes that require user"""

            response = VerificationService.check_verification_mode(USER_PHONE, mode)
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert response.data["detail"] == "User not found."

        @pytest.mark.parametrize(
            "mode",
            [
                Verification.Mode.RESET_PASSWORD,
                Verification.Mode.CHANGE_PASSWORD,
            ],
        )
        def test_returns_none_for_admin_trying_privileged_actions(self, admin_user, mode):
            """Should return None for modes that allow missing user"""

            response = VerificationService.check_verification_mode(ADMIN_PHONE, mode)
            assert response is None

        @pytest.mark.parametrize(
            "mode",
            [
                Verification.Mode.RESET_PASSWORD,
                Verification.Mode.CHANGE_PASSWORD,
            ],
        )
        def test_returns_error_for_user_trying_privileged_actions(self, user, mode):
            """Should return 403 if regular user tries privileged modes"""

            response = VerificationService.check_verification_mode(user.phone, mode)
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert response.data["detail"] == "You do not have permission to perform this action."

        def test_returns_none_for_non_existed_new_phone(self):
            """Superuser should be allowed to change password"""

            response = VerificationService.check_verification_mode(USER_PHONE, Verification.Mode.CHANGE_PHONE_NEW)
            assert response is None

        def test_returns_error_for_active_user_on_change_phone_new(self, user):
            """Should return 403 if active user tries to use CHANGE_PHONE_NEW"""

            response = VerificationService.check_verification_mode(user.phone, Verification.Mode.CHANGE_PHONE_NEW)
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert response.data["detail"] == "This new phone number already exists."

        def test_returns_error_for_superuser_on_delete_account(self, superuser):
            """Should return 403 if superuser tries to use DELETE_ACCOUNT"""

            response = VerificationService.check_verification_mode(superuser.phone, Verification.Mode.DELETE_ACCOUNT)
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert response.data["detail"] == "Superuser account cannot be deleted."

    class TestCheckVerificationObject:
        def test_returns_error_if_none(self):
            response = VerificationService._check_verification_object(None, USER_PHONE)
            assert response.status_code == status.HTTP_404_NOT_FOUND

        def test_returns_error_if_phone_mismatch(self, verification):
            response = VerificationService._check_verification_object(verification, OTHER_PHONE)

            assert response.status_code == status.HTTP_400_BAD_REQUEST

        def test_returns_none_if_success(self, verification):
            response = VerificationService._check_verification_object(verification, verification.phone)

            assert response is None

    class TestValidateVerificationIsUsable:
        def test_returns_error_if_not_found(self):
            response = VerificationService.validate_verification_is_usable(USER_PHONE, "none")

            assert response.status_code == status.HTTP_404_NOT_FOUND

        def test_returns_error_if_phone_mismatch(self, verification):
            response = VerificationService.validate_verification_is_usable(OTHER_PHONE, verification.verification_token)

            assert response.status_code == status.HTTP_400_BAD_REQUEST

        @pytest.mark.parametrize("status_value", [Verification.Status.VERIFIED, Verification.Status.USED])
        def test_returns_conflict_if_used_or_verified(self, create_verification, status_value):
            verification = create_verification(status=status_value)
            response = VerificationService.validate_verification_is_usable(
                verification.phone, verification.verification_token
            )

            assert response.status_code == status.HTTP_409_CONFLICT

        def test_returns_gone_if_expired(self, expired_verification):
            response = VerificationService.validate_verification_is_usable(
                expired_verification.phone, expired_verification.verification_token
            )

            assert response.status_code == status.HTTP_410_GONE

        def test_returns_none_if_success(self, verification):
            response = VerificationService.validate_verification_is_usable(
                verification.phone, verification.verification_token
            )

            assert response is None

    class TestGetVerifiedVerificationOrError:
        def test_successful_verification(self, create_verification):
            """Should return verification object when all checks pass"""

            verification = Verification.objects.create(
                phone=USER_PHONE,
                verification_token="token",
                mode=Verification.Mode.LOGIN,
                status=Verification.Status.VERIFIED,
            )

            response, error = VerificationService.get_verified_verification_or_error(
                verification.phone, verification.verification_token, verification.mode
            )

            assert response == verification

        def test_returns_error_if_not_found(self):
            """Should return 404 if token not found"""

            response, error = VerificationService.get_verified_verification_or_error(
                USER_PHONE, "missing_token", Verification.Mode.LOGIN
            )

            assert response is None
            assert error.status_code == status.HTTP_404_NOT_FOUND
            assert error.data["detail"] == "Verification not found."

        def test_returns_error_if_phone_mismatch(self, verification):
            """Should return 400 if phone does not match"""

            response, error = VerificationService.get_verified_verification_or_error(
                OTHER_PHONE, verification.verification_token, verification.mode
            )

            assert response is None
            assert error.status_code == status.HTTP_400_BAD_REQUEST
            assert error.data["detail"] == "Phone number does not match the verification record."

        def test_returns_error_if_mode_mismatch(self, verification):
            """Should return 404 if mode does not match"""

            response, error = VerificationService.get_verified_verification_or_error(
                USER_PHONE, verification.verification_token, Verification.Mode.RESET_PASSWORD
            )

            assert response is None
            assert error.status_code == status.HTTP_400_BAD_REQUEST
            assert error.data["detail"] == "Invalid verification mode."

        def test_returns_error_if_status_sent(self, create_verification):
            """Should return 400 if status is SENT"""

            create_verification(
                phone=USER_PHONE,
                verification_token="new_token",
                mode=Verification.Mode.LOGIN,
                status=Verification.Status.SENT,
            )

            response, error = VerificationService.get_verified_verification_or_error(
                USER_PHONE, "new_token", Verification.Mode.LOGIN
            )

            assert response is None
            assert error.status_code == status.HTTP_400_BAD_REQUEST
            assert error.data["detail"] == "Phone number has not been verified."

        def test_returns_error_if_status_used(self, create_verification):
            create_verification(
                phone=USER_PHONE,
                verification_token="used_token",
                mode=Verification.Mode.LOGIN,
                status=Verification.Status.USED,
            )

            response, error = VerificationService.get_verified_verification_or_error(
                USER_PHONE, "used_token", Verification.Mode.LOGIN
            )

            assert response is None
            assert error.status_code == status.HTTP_409_CONFLICT
            assert error.data["detail"] == "This code has already been used. Please request a new one."

        def test_returns_error_if_status_expired(self, create_verification):
            create_verification(
                phone=USER_PHONE,
                verification_token="expired_token",
                mode=Verification.Mode.LOGIN,
                status=Verification.Status.EXPIRED,
            )

            response, error = VerificationService.get_verified_verification_or_error(
                USER_PHONE, "expired_token", Verification.Mode.LOGIN
            )

            assert response is None
            assert error.status_code == status.HTTP_410_GONE
            assert error.data["detail"] == "This code has expired. Please request a new one."


@pytest.mark.django_db
class TestVerificationModel:
    def test_str_representation(self, verification):
        """Test string representation of Verification object"""

        expected = (
            f"{verification.phone} - {verification.mode} - {verification.status} - {verification.verification_token}"
        )
        assert str(verification) == expected

    def test_get_verification_by_token(self, verification):
        """Test retrieving a verification entry by token."""

        retrieved = Verification.get_verification_by_token(verification.verification_token)

        assert retrieved is not None
        assert retrieved.verification_token == verification.verification_token

    def test_get_recent_verification_returns_most_recent_within_delay(self, create_verification):
        """Returns only the most recent verification within resend delay."""

        create_verification(created_at=now() - timedelta(seconds=VERIFICATION_CODE_RESEND_DELAY + 10))  # old
        recent = create_verification(created_at=now() - timedelta(seconds=VERIFICATION_CODE_RESEND_DELAY - 10))

        result = Verification.get_recent_verification(USER_PHONE)
        assert result == recent

    def test_get_recent_verification_returns_none_if_all_expired(self, create_verification):
        """Returns None if no verifications are within resend delay."""

        create_verification(created_at=now() - timedelta(seconds=VERIFICATION_CODE_RESEND_DELAY + 10))

        result = Verification.get_recent_verification(USER_PHONE)
        assert result is None

    def test_get_recent_verification_returns_none_if_other_status(self, create_verification):
        """Returns None if no verifications are within resend delay."""

        create_verification(created_at=now() - timedelta(seconds=VERIFICATION_CODE_RESEND_DELAY + 10))
        create_verification(
            created_at=now() - timedelta(seconds=VERIFICATION_CODE_RESEND_DELAY - 10), status=Verification.Status.USED
        )

        result = Verification.get_recent_verification(USER_PHONE)
        assert result is None
