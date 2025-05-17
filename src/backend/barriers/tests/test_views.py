from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework import status

from action_history.models import BarrierActionLog
from barriers.models import BarrierLimit, UserBarrier
from phones.models import BarrierPhone


@pytest.mark.django_db
class TestListBarriersView:
    def test_list_public_barriers(self, authenticated_client, barrier, private_barrier):
        response = authenticated_client.get(reverse("list_barriers"))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_count"] == 1
        assert response.data["barriers"][0]["id"] == barrier.id


@pytest.mark.django_db
class TestMyBarriersListView:
    def test_list_my_barriers(self, authenticated_client, user, private_barrier_with_access):
        response = authenticated_client.get(reverse("my_barriers"))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_count"] == 1
        assert response.data["barriers"][0]["id"] == private_barrier_with_access.id

    def test_without_access_not_included(self, authenticated_client, user, barrier):
        response = authenticated_client.get(reverse("my_barriers"))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_count"] == 0

    def test_inactive_access_not_included(self, authenticated_client, user, private_barrier_with_access):
        user_barrier = UserBarrier.objects.get(user=user, barrier=private_barrier_with_access)
        user_barrier.is_active = False
        user_barrier.save()

        response = authenticated_client.get(reverse("my_barriers"))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_count"] == 0

    def test_inactive_barrier_not_included(self, authenticated_client, user, private_barrier_with_access):
        private_barrier_with_access.is_active = False
        private_barrier_with_access.save()

        response = authenticated_client.get(reverse("my_barriers"))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_count"] == 0


@pytest.mark.django_db
class TestBarrierView:
    def test_get_public_barrier(self, authenticated_client, barrier):
        url = reverse("get_barrier", args=[barrier.id])
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == barrier.id

    def test_get_private_barrier_with_access(self, authenticated_client, user, private_barrier_with_access):
        url = reverse("get_barrier", args=[private_barrier_with_access.id])
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == private_barrier_with_access.id

    def test_get_private_barrier_without_access(self, authenticated_client, user, private_barrier):
        url = reverse("get_barrier", args=[private_barrier.id])
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["detail"] == "You do not have access to this barrier."

    def test_barrier_not_found_returns_error(self, authenticated_client):
        url = reverse("get_barrier", args=[99999])
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["detail"] == "Barrier not found."


@pytest.mark.django_db
class TestBarrierLimitView:
    def test_public_barrier_with_no_limits_creates_one(self, authenticated_client, barrier):
        url = reverse("get_barrier_limits", args=[barrier.id])
        assert not hasattr(barrier, "limits")  # Ensure no limit initially

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert BarrierLimit.objects.filter(barrier=barrier).exists()

    def test_public_barrier_with_limits(self, authenticated_client, barrier):
        BarrierLimit.objects.create(
            barrier=barrier,
            user_phone_limit=3,
            user_temp_phone_limit=1,
            global_temp_phone_limit=10,
            sms_weekly_limit=50,
        )

        url = reverse("get_barrier_limits", args=[barrier.id])
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["user_phone_limit"] == 3
        assert response.data["sms_weekly_limit"] == 50

    def test_private_barrier_with_access_and_no_limit_creates_one(
        self, authenticated_client, private_barrier_with_access
    ):
        url = reverse("get_barrier_limits", args=[private_barrier_with_access.id])
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert BarrierLimit.objects.filter(barrier=private_barrier_with_access).exists()

    def test_owner_can_view_limits(self, authenticated_admin_client, private_barrier):
        url = reverse("get_barrier_limits", args=[private_barrier.id])
        response = authenticated_admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data is not None

    def test_private_barrier_without_access(self, authenticated_client, private_barrier):
        url = reverse("get_barrier_limits", args=[private_barrier.id])
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["detail"] == "You do not have access to this barrier."

    def test_barrier_not_found_returns_error(self, authenticated_client):
        url = reverse("get_barrier_limits", args=[99999])
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["detail"] == "Barrier not found."


@pytest.mark.django_db
class TestLeaveBarrierView:
    def test_user_can_leave_barrier(self, authenticated_client, user, private_barrier_with_access):
        url = reverse("leave_barrier", args=[private_barrier_with_access.id])
        response = authenticated_client.delete(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Left the barrier successfully."

        user_barrier = UserBarrier.objects.get(user=user, barrier=private_barrier_with_access)
        assert not user_barrier.is_active

    def test_user_cannot_leave_barrier_without_access(self, authenticated_client, barrier):
        url = reverse("leave_barrier", args=[barrier.id])
        response = authenticated_client.delete(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["detail"] == "You do not have access to this barrier."

    def test_barrier_not_found_returns_error(self, authenticated_client):
        url = reverse("leave_barrier", args=[99999])
        response = authenticated_client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["detail"] == "Barrier not found."

    @patch.object(BarrierPhone, "send_sms_to_delete")
    def test_all_user_phones_are_removed_on_leave(
        self, mock_send_sms, authenticated_client, user, private_barrier_with_access
    ):
        barrier = private_barrier_with_access
        url = reverse("leave_barrier", args=[barrier.id])

        BarrierPhone.objects.create(
            user=user,
            barrier=barrier,
            phone=user.phone,
            type=BarrierPhone.PhoneType.PRIMARY,
            device_serial_number=1,
        )
        BarrierPhone.objects.create(
            user=user,
            barrier=barrier,
            phone="+79998887766",
            type=BarrierPhone.PhoneType.PERMANENT,
            device_serial_number=2,
        )

        response = authenticated_client.delete(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Left the barrier successfully."

        user_barrier = UserBarrier.objects.get(user=user, barrier=barrier)
        assert not user_barrier.is_active

        phones = BarrierPhone.objects.filter(user=user, barrier=barrier)
        assert all(not phone.is_active for phone in phones)

        for phone in phones:
            log = BarrierActionLog.objects.get(
                phone=phone,
                barrier=barrier,
                author=BarrierActionLog.Author.USER,
                action_type=BarrierActionLog.ActionType.DELETE_PHONE,
                reason=BarrierActionLog.Reason.BARRIER_EXIT,
            )
            assert log.old_value is None
            assert log.new_value is None

        assert mock_send_sms.call_count == 2


@pytest.mark.django_db
class TestBarrierAccessCheckView:
    def test_has_access_to_private_barrier(self, authenticated_client, private_barrier_with_access):
        url = reverse("barrier_has_access", args=[private_barrier_with_access.id])
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["has_access"] is True

    def test_no_access_to_private_barrier(self, authenticated_client, private_barrier):
        url = reverse("barrier_has_access", args=[private_barrier.id])
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["has_access"] is False

    def test_no_access_to_public_barrier(self, authenticated_client, barrier):
        url = reverse("barrier_has_access", args=[barrier.id])
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["has_access"] is False

    def test_inactive_barrier_returns_404(self, authenticated_client, private_barrier_with_access):
        private_barrier_with_access.is_active = False
        private_barrier_with_access.save()

        url = reverse("barrier_has_access", args=[private_barrier_with_access.id])
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["detail"] == "Barrier not found."
