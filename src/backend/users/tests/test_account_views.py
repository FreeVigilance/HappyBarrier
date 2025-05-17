from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework import status

from action_history.models import BarrierActionLog
from barriers.models import UserBarrier
from conftest import ADMIN_PASSWORD, OTHER_PHONE
from phones.models import BarrierPhone
from users.account_views import ChangePhoneView
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

    @patch.object(BarrierPhone, "send_sms_to_delete")
    def test_delete_user_deactivates_links_and_phones(
        self,
        mock_send_sms,
        authenticated_client,
        user,
        delete_verification,
        barrier,
        create_barrier_phone,
    ):
        access_request = barrier.access_requests.create(user=user, status="accepted", request_type="from_user")
        UserBarrier.objects.create(user=user, barrier=barrier, access_request=access_request)

        phone, _ = create_barrier_phone(user, barrier)

        response = authenticated_client.delete(
            reverse("user_account"), {"verification_token": delete_verification.verification_token}
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        user.refresh_from_db()
        assert not user.is_active

        user_barrier = UserBarrier.objects.get(user=user, barrier=barrier)
        assert not user_barrier.is_active

        phone.refresh_from_db()
        assert not phone.is_active

        mock_send_sms.assert_called_once()
        called_log = mock_send_sms.call_args.args[0]
        assert called_log.phone == phone
        assert called_log.reason == BarrierActionLog.Reason.USER_DELETED
        assert called_log.action_type == BarrierActionLog.ActionType.DELETE_PHONE

    def test_delete_user_account_invalid_verification(self, authenticated_client, create_verification):
        """Test deleting user account with invalid verification token"""

        verification_token = create_verification(mode=Verification.Mode.LOGIN).verification_token

        response = authenticated_client.delete(reverse("user_account"), {"verification_token": verification_token})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["detail"] == "Invalid verification mode."

    def test_delete_superuser_account_raises(self, api_client, superuser, create_verification):
        """Test deleting superuser account"""

        api_client.force_authenticate(user=superuser)

        verification_token = create_verification(mode=Verification.Mode.DELETE_ACCOUNT).verification_token

        response = api_client.delete(reverse("user_account"), {"verification_token": verification_token})

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["detail"] == "Superuser account cannot be deleted."

    @patch.object(BarrierPhone, "send_sms_to_delete")
    def test_delete_admin_account_deactivates_owned_barriers(
        self,
        mock_send_sms,
        authenticated_admin_client,
        barrier,
        admin_user,
        create_verification,
        create_barrier_phone,
        create_access_request,
    ):
        """Test deleting admin also deactivates their barriers"""

        access_request = create_access_request(user=admin_user, barrier=barrier, status="accepted")
        UserBarrier.objects.create(user=admin_user, barrier=barrier, access_request=access_request)
        phone, _ = create_barrier_phone(admin_user, barrier)
        verification = create_verification(
            admin_user.phone, Verification.Status.VERIFIED, Verification.Mode.DELETE_ACCOUNT
        )

        url = reverse("user_account")
        data = {"verification_token": verification.verification_token}
        response = authenticated_admin_client.delete(url, data)

        assert response.status_code == status.HTTP_204_NO_CONTENT

        admin_user.refresh_from_db()
        assert not admin_user.is_active

        barrier.refresh_from_db()
        assert not barrier.is_active

        phone.refresh_from_db()
        assert not phone.is_active

        mock_send_sms.assert_called_once()
        log = mock_send_sms.call_args.args[0]
        assert log.phone == phone
        assert log.reason == BarrierActionLog.Reason.USER_DELETED

    def test_put_method_not_allowed(self, authenticated_client):
        """Test that PUT method is not allowed on user account view"""

        response = authenticated_client.put(reverse("user_account"), {})

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert response.data["detail"] == 'Method "PUT" not allowed.'


@pytest.mark.django_db
class TestChangePhoneView:
    """Tests for ChangePhoneView"""

    @patch.object(ChangePhoneView, "update_primary_phones_on_user_change")
    def test_change_phone_success(
        self, mock_update_phones, authenticated_client, user, old_phone_verification, new_phone_verification
    ):
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

        mock_update_phones.assert_called_once_with(user, old_phone_verification.phone, OTHER_PHONE)

    @patch.object(BarrierPhone, "send_sms_to_delete")
    @patch.object(BarrierPhone, "send_sms_to_create")
    class TestChangePhonePrimaryReplacement:
        def test_primary_phone_replaced_on_change(
            self,
            mock_send_create,
            mock_send_delete,
            authenticated_client,
            user,
            private_barrier_with_access,
            create_access_request,
            old_phone_verification,
            new_phone_verification,
            create_barrier_phone,
        ):
            barrier = private_barrier_with_access

            old_phone = user.phone
            new_phone = OTHER_PHONE

            old_phone_obj, _ = create_barrier_phone(user, barrier, phone=old_phone, type=BarrierPhone.PhoneType.PRIMARY)

            data = {
                "new_phone": new_phone,
                "old_verification_token": old_phone_verification.verification_token,
                "new_verification_token": new_phone_verification.verification_token,
            }

            response = authenticated_client.patch(reverse("change_phone"), data)
            assert response.status_code == status.HTTP_200_OK

            user.refresh_from_db()
            assert user.phone == new_phone

            old_phone_obj.refresh_from_db()
            assert not old_phone_obj.is_active

            new_phone_obj = BarrierPhone.objects.get(
                user=user,
                barrier=barrier,
                phone=new_phone,
                type=BarrierPhone.PhoneType.PRIMARY,
                is_active=True,
            )

            assert new_phone_obj is not None
            mock_send_delete.assert_called_once()
            mock_send_create.assert_called_once()

            delete_log = BarrierActionLog.objects.get(
                phone=old_phone_obj,
                action_type=BarrierActionLog.ActionType.DELETE_PHONE,
                reason=BarrierActionLog.Reason.PRIMARY_PHONE_CHANGE,
            )
            assert delete_log.author == BarrierActionLog.Author.SYSTEM
            assert delete_log.old_value is None
            assert delete_log.new_value is None

            create_log = BarrierActionLog.objects.get(
                phone=new_phone_obj,
                action_type=BarrierActionLog.ActionType.ADD_PHONE,
                reason=BarrierActionLog.Reason.PRIMARY_PHONE_CHANGE,
            )
            assert create_log.author == BarrierActionLog.Author.SYSTEM
            assert create_log.old_value is None
            assert create_log.new_value == new_phone_obj.describe_phone_params()


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
