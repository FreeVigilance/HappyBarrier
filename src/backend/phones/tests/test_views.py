import json
from datetime import time
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework import status

from action_history.models import BarrierActionLog
from phones.models import BarrierPhone


@pytest.mark.django_db
class TestCreateBarrierPhoneView:
    def user_url(self, barrier):
        return reverse("user_create_barrier_phone_view", kwargs={"id": barrier.id})

    def admin_url(self, barrier):
        return reverse("admin_create_barrier_phone_view", kwargs={"id": barrier.id})

    @patch.object(BarrierPhone, "send_sms_to_create")
    def test_user_creates_phone_successfully(
        self, mock_send_sms, authenticated_client, user, private_barrier_with_access
    ):
        url = self.user_url(private_barrier_with_access)
        data = {
            "phone": user.phone,
            "type": BarrierPhone.PhoneType.PRIMARY,
            "name": "Main Phone",
        }

        response = authenticated_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert BarrierPhone.objects.filter(user=user, barrier=private_barrier_with_access, phone=user.phone).exists()
        mock_send_sms.assert_called_once()

    @patch.object(BarrierPhone, "send_sms_to_create")
    def test_admin_creates_phone_for_user(self, mock_send_sms, authenticated_admin_client, admin_user, user, barrier):
        url = self.admin_url(barrier)
        data = {
            "phone": user.phone,
            "type": BarrierPhone.PhoneType.PRIMARY,
            "name": "Admin Phone",
            "user": user.id,
        }

        response = authenticated_admin_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert BarrierPhone.objects.filter(user=user, barrier=barrier).exists()
        mock_send_sms.assert_called_once()

    def test_barrier_not_found(self, authenticated_client, user):
        url = reverse("user_create_barrier_phone_view", kwargs={"id": 999999})
        data = {
            "phone": user.phone,
            "type": BarrierPhone.PhoneType.PRIMARY,
            "name": "Test",
        }

        response = authenticated_client.post(url, data)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["detail"] == "Barrier not found."

    def test_admin_barrier_permission_denied(self, authenticated_admin_client, other_barrier, user):
        url = reverse("admin_create_barrier_phone_view", kwargs={"id": other_barrier.id})
        data = {
            "phone": user.phone,
            "type": BarrierPhone.PhoneType.PRIMARY,
            "name": "Test",
            "user": user.id,
        }

        response = authenticated_admin_client.post(url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["detail"] == "You do not have access to this barrier."

    def test_user_barrier_permission_denied(self, authenticated_client, barrier, user):
        url = reverse("user_create_barrier_phone_view", kwargs={"id": barrier.id})
        data = {
            "phone": user.phone,
            "type": BarrierPhone.PhoneType.PRIMARY,
            "name": "Test",
        }

        response = authenticated_client.post(url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["detail"] == "You do not have access to this barrier."

    def test_admin_user_not_found(self, authenticated_admin_client, barrier):
        url = self.admin_url(barrier)
        data = {
            "phone": "+79991112233",
            "type": BarrierPhone.PhoneType.PRIMARY,
            "name": "Test",
            "user": 999999,
        }

        response = authenticated_admin_client.post(url, data)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["detail"] == "User not found."

    def test_admin_missing_user_field(self, authenticated_admin_client, barrier):
        url = self.admin_url(barrier)
        data = {
            "phone": "+79991112233",
            "type": BarrierPhone.PhoneType.PERMANENT,
            "name": "No User",
        }

        response = authenticated_admin_client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "user" in response.data


@pytest.mark.django_db
class TestBarrierPhoneListViews:
    def user_url(self, barrier):
        return reverse("user_barrier_phone_list_view", kwargs={"id": barrier.id})

    def admin_url(self, barrier):
        return reverse("admin_barrier_phone_list_view", kwargs={"id": barrier.id})

    def test_user_sees_own_phones(self, authenticated_client, user, private_barrier_with_access, create_barrier_phone):
        create_barrier_phone(user, private_barrier_with_access)

        url = self.user_url(private_barrier_with_access)
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "phones" in response.data
        assert len(response.data["phones"]) == 1

    def test_admin_sees_all_phones_in_barrier(
        self, authenticated_admin_client, admin_user, user, barrier, barrier_phone
    ):
        url = self.admin_url(barrier)
        response = authenticated_admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "phones" in response.data
        assert len(response.data["phones"]) == 1

    def test_filters_apply_correctly(self, authenticated_admin_client, user, barrier, create_barrier_phone):
        create_barrier_phone(user, barrier, phone=user.phone, name="Alice", type=BarrierPhone.PhoneType.PRIMARY)
        create_barrier_phone(user, barrier, phone="+70000000002", name="Bob", type=BarrierPhone.PhoneType.PERMANENT)

        url = self.admin_url(barrier)

        # Filter by name
        response = authenticated_admin_client.get(url, {"name": "Alice"})
        assert len(response.data["phones"]) == 1

        # Filter by phone
        response = authenticated_admin_client.get(url, {"phone": "00000002"})
        assert len(response.data["phones"]) == 1

        # Filter by type
        response = authenticated_admin_client.get(url, {"type": BarrierPhone.PhoneType.PERMANENT})
        assert len(response.data["phones"]) == 1

    def test_invalid_barrier_id_returns_404(self, authenticated_client):
        url = reverse("user_barrier_phone_list_view", kwargs={"id": 999999})
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["detail"] == "Barrier not found."

    def test_non_owner_user_gets_403_from_admin_view(self, authenticated_admin_client, other_barrier):
        url = self.admin_url(other_barrier)
        response = authenticated_admin_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["detail"] == "You do not have access to this barrier."

    def test_is_active_filter_in_list_view(self, authenticated_admin_client, user, barrier, create_barrier_phone):
        create_barrier_phone(user, barrier, phone="+70000000001")

        inactive, _ = create_barrier_phone(user, barrier, phone="+70000000002")
        inactive.is_active = False
        inactive.save()

        url = self.admin_url(barrier)

        response = authenticated_admin_client.get(url)
        assert len(response.data["phones"]) == 1

        response = authenticated_admin_client.get(url, {"is_active": "false"})
        assert len(response.data["phones"]) == 1
        assert response.data["phones"][0]["phone"] == "+70000000002"

        response = authenticated_admin_client.get(url, {"is_active": "invalid"})
        assert len(response.data["phones"]) == 1
        assert response.data["phones"][0]["phone"] == "+70000000001"


@pytest.mark.django_db
class TestBarrierPhoneDetailViews:
    base_url = "user_barrier_phone_view"
    base_url_admin = "admin_barrier_phone_view"

    def test_user_can_retrieve_own_phone(self, authenticated_client, barrier_phone):
        barrier_phone, _ = barrier_phone
        url = reverse(self.base_url, args=[barrier_phone.id])
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["phone"] == barrier_phone.phone

    def test_user_cannot_retrieve_other_phone(self, authenticated_client, another_user, barrier, create_barrier_phone):
        other_user_phone, _ = create_barrier_phone(another_user, barrier)
        url = reverse(self.base_url, args=[other_user_phone.id])
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["detail"] == "You do not have access to this phone."

    def test_admin_can_retrieve_phone(self, authenticated_admin_client, user, barrier, barrier_phone):
        barrier_phone, _ = barrier_phone
        url = reverse(self.base_url_admin, args=[barrier_phone.id])
        response = authenticated_admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["phone"] == barrier_phone.phone

    def test_admin_cannot_access_phone_in_foreign_barrier(
        self, authenticated_admin_client, user, other_barrier, create_barrier_phone
    ):
        other_user_phone, _ = create_barrier_phone(user, other_barrier)
        url = reverse(self.base_url_admin, args=[other_user_phone.id])
        response = authenticated_admin_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["detail"] == "You do not have access to this phone."

    def test_patch_updates_phone(self, authenticated_client, barrier_phone):
        barrier_phone, _ = barrier_phone
        url = reverse(self.base_url, args=[barrier_phone.id])
        data = {"name": "Updated Name"}
        response = authenticated_client.patch(url, data=json.dumps(data), content_type="application/json")
        assert response.status_code == status.HTTP_200_OK
        barrier_phone.refresh_from_db()
        assert barrier_phone.name == "Updated Name"

    def test_patch_fails_on_inactive_phone(self, authenticated_client, barrier_phone):
        barrier_phone, _ = barrier_phone
        barrier_phone.is_active = False
        barrier_phone.save()

        url = reverse(self.base_url, args=[barrier_phone.id])
        data = {"name": "Blocked update"}
        response = authenticated_client.patch(url, data=json.dumps(data), content_type="application/json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["detail"] == "Cannot update a deactivated phone."

    def test_put_method_not_allowed(self, authenticated_client, barrier_phone):
        barrier_phone, _ = barrier_phone
        url = reverse(self.base_url, args=[barrier_phone.id])
        response = authenticated_client.put(url)
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert response.data["detail"].lower() == 'method "put" not allowed.'

    @patch.object(BarrierPhone, "send_sms_to_delete")
    def test_user_can_delete_phone(self, mock_send_sms, authenticated_client, barrier, user, barrier_phone):
        barrier_phone, _ = barrier_phone
        url = reverse(self.base_url, args=[barrier_phone.id])
        response = authenticated_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        barrier_phone.refresh_from_db()
        assert not barrier_phone.is_active
        mock_send_sms.assert_called_once()

        log = BarrierActionLog.objects.get(phone=barrier_phone, action_type=BarrierActionLog.ActionType.DELETE_PHONE)
        assert log.reason == BarrierActionLog.Reason.MANUAL
        assert log.author == BarrierActionLog.Author.USER

    def test_user_cannot_delete_primary_phone(self, authenticated_client, barrier, user, create_barrier_phone):
        phone, _ = create_barrier_phone(user, barrier, phone=user.phone, type=BarrierPhone.PhoneType.PRIMARY)
        url = reverse(self.base_url, args=[phone.id])
        response = authenticated_client.delete(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["detail"] == "Primary phone number cannot be deleted."

    @patch.object(BarrierPhone, "send_sms_to_delete")
    def test_cannot_delete_already_inactive_phone(self, mock_send_sms, authenticated_client, barrier_phone):
        barrier_phone, _ = barrier_phone
        barrier_phone.is_active = False
        barrier_phone.save()

        url = reverse(self.base_url, args=[barrier_phone.id])
        response = authenticated_client.delete(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["detail"] == "Phone is already deactivated."
        mock_send_sms.assert_not_called()


@pytest.mark.django_db
class TestBarrierPhoneScheduleView:
    base_url = "user_barrier_phone_schedule_view"
    base_url_admin = "admin_barrier_phone_schedule_view"

    def test_get_schedule(self, authenticated_client, schedule_barrier_phone):
        phone, _ = schedule_barrier_phone
        url = reverse(self.base_url, args=[phone.id])
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data["monday"], list)

    def test_get_fails_if_phone_not_schedule_type(self, authenticated_client, barrier_phone):
        barrier_phone, _ = barrier_phone
        url = reverse(self.base_url, args=[barrier_phone.id])
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["detail"] == "Only schedule-type phones have a schedule."

    def test_get_not_found(self, authenticated_client):
        url = reverse(self.base_url, args=[999999])
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["detail"] == "Phone not found."

    def test_patch_not_allowed(self, authenticated_client, schedule_barrier_phone):
        phone, _ = schedule_barrier_phone
        url = reverse(self.base_url, args=[phone.id])
        response = authenticated_client.patch(url)
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_user_cannot_access_foreign_phone(self, authenticated_client, another_user, barrier, create_barrier_phone):
        schedule = {"monday": [{"start_time": time(9, 0), "end_time": time(10, 0)}]}
        phone, _ = create_barrier_phone(another_user, barrier, type=BarrierPhone.PhoneType.SCHEDULE, schedule=schedule)
        url = reverse(self.base_url, args=[phone.id])
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["detail"] == "You do not have access to this phone."

    def test_admin_cannot_access_foreign_barrier_phone(
        self, authenticated_admin_client, user, other_barrier, create_barrier_phone
    ):
        schedule = {"tuesday": [{"start_time": time(14, 0), "end_time": time(15, 0)}]}
        phone, _ = create_barrier_phone(user, other_barrier, type=BarrierPhone.PhoneType.SCHEDULE, schedule=schedule)
        url = reverse(self.base_url_admin, args=[phone.id])
        response = authenticated_admin_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["detail"] == "You do not have access to this phone."

    @patch("phones.serializers.ScheduleTimeInterval.replace_schedule")
    @patch("phones.serializers.validate_schedule_phone")
    @patch("phones.serializers.PhoneTaskManager.edit_tasks")
    def test_put_schedule_success(
        self, mock_edit, mock_validate, mock_replace, authenticated_client, schedule_barrier_phone
    ):
        phone, _ = schedule_barrier_phone
        url = reverse(self.base_url, args=[phone.id])
        data = {
            "monday": [{"start_time": "09:00", "end_time": "10:00"}],
            "tuesday": [{"start_time": "11:00", "end_time": "12:00"}],
        }

        response = authenticated_client.put(url, data=json.dumps(data), content_type="application/json")
        assert response.status_code == status.HTTP_200_OK
        assert "monday" in response.data
        mock_validate.assert_called_once()
        mock_replace.assert_called_once()
        mock_edit.assert_called_once()

    def test_put_rejected_if_inactive(self, authenticated_client, schedule_barrier_phone):
        phone, _ = schedule_barrier_phone
        phone.is_active = False
        phone.save()

        url = reverse(self.base_url, args=[phone.id])
        data = {
            "monday": [{"start_time": "09:00", "end_time": "10:00"}],
        }

        response = authenticated_client.put(url, data=json.dumps(data), content_type="application/json")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["detail"] == "Cannot update a deactivated phone."
