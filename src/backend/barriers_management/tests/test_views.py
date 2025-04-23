import pytest
from django.urls import reverse
from rest_framework import status

from access_requests.models import AccessRequest
from barriers.models import Barrier, BarrierLimit, UserBarrier
from conftest import BARRIER_ADDRESS, BARRIER_DEVICE_PASSWORD, BARRIER_DEVICE_PHONE, OTHER_PHONE, USER_PHONE
from users.models import User


@pytest.mark.django_db
class TestCreateBarrierView:
    def test_create_barrier_success(self, authenticated_admin_client, admin_user):
        url = reverse("create_barrier")
        data = {
            "address": BARRIER_ADDRESS,
            "device_phone": BARRIER_DEVICE_PHONE,
            "device_model": Barrier.Model.RTU5025,
            "device_phones_amount": 1,
            "device_password": BARRIER_DEVICE_PASSWORD,
            "additional_info": "Test barrier",
            "is_public": True,
        }

        response = authenticated_admin_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["address"] == BARRIER_ADDRESS.lower()
        assert response.data["device_phone"] == BARRIER_DEVICE_PHONE
        assert response.data["owner"] == admin_user.id
        assert "device_password" not in response.data

        # Ensure BarrierLimit is created
        barrier_id = response.data["id"]
        assert BarrierLimit.objects.filter(barrier_id=barrier_id).exists()


@pytest.mark.django_db
class TestMyAdminBarrierView:
    def test_admin_list_own_barriers(self, authenticated_admin_client, barrier):
        url = reverse("admin_my_barriers")
        response = authenticated_admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_count"] == 1
        assert response.data["barriers"][0]["address"] == barrier.address

    def test_no_barriers_returns_empty_list(self, authenticated_admin_client):
        url = reverse("admin_my_barriers")
        response = authenticated_admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_count"] == 0
        assert response.data["barriers"] == []

    def test_sort_by_created_at(self, authenticated_admin_client, admin_user, barrier, other_admin_barrier):
        response = authenticated_admin_client.get(reverse("admin_my_barriers") + "?ordering=created_at")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["barriers"][0]["id"] == barrier.id
        assert response.data["barriers"][1]["id"] == other_admin_barrier.id

        assert response.data["barriers"][0]["created_at"] <= response.data["barriers"][1]["created_at"]

    def test_sort_descending_updated_at(self, authenticated_admin_client, admin_user, barrier, other_admin_barrier):
        barrier.device_password = "1235"
        barrier.save()

        response = authenticated_admin_client.get(reverse("admin_my_barriers") + "?ordering=-updated_at")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["barriers"][0]["id"] == barrier.id
        assert response.data["barriers"][1]["id"] == other_admin_barrier.id

    def test_invalid_ordering_fallbacks_to_default(
        self, authenticated_admin_client, admin_user, barrier, other_admin_barrier
    ):
        response = authenticated_admin_client.get(reverse("admin_my_barriers") + "?ordering=invalid_field")

        assert response.status_code == status.HTTP_200_OK
        addresses = [b["address"] for b in response.data["barriers"]]
        assert addresses == sorted(addresses)

    def test_admin_sees_only_own_barriers(self, authenticated_admin_client, admin_user, another_admin, other_barrier):
        response = authenticated_admin_client.get(reverse("admin_my_barriers"))

        assert response.status_code == status.HTTP_200_OK
        for barr in response.data["barriers"]:
            assert barr["owner"]["phone"] == admin_user.phone


@pytest.mark.django_db
class TestAdminBarrierView:
    def test_admin_get_own_barrier(self, authenticated_admin_client, admin_user, barrier):
        url = reverse("admin_barrier_view", args=[barrier.id])
        response = authenticated_admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["address"] == barrier.address

    def test_admin_cannot_get_foreign_barrier(self, authenticated_admin_client, admin_user, other_barrier):
        url = reverse("admin_barrier_view", args=[other_barrier.id])
        response = authenticated_admin_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["detail"] == "You do not have permission to access this barrier."

    def test_admin_update_barrier(self, authenticated_admin_client, admin_user, barrier):
        url = reverse("admin_barrier_view", args=[barrier.id])
        data = {
            "device_password": "0000",
            "additional_info": "Updated description",
        }

        response = authenticated_admin_client.patch(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["additional_info"] == "Updated description"

    def test_admin_update_barrier_invalid_password(self, authenticated_admin_client, admin_user, barrier):
        url = reverse("admin_barrier_view", args=[barrier.id])
        data = {"device_password": "updatedpass"}

        response = authenticated_admin_client.patch(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Enter a valid device password. Must be exactly 4 digits." in response.data["non_field_errors"]

    def test_admin_delete_barrier(self, authenticated_admin_client, admin_user, barrier):
        url = reverse("admin_barrier_view", args=[barrier.id])
        response = authenticated_admin_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT

        barrier.refresh_from_db()
        assert not barrier.is_active

    def test_put_method_not_allowed(self, authenticated_admin_client, admin_user, barrier):
        url = reverse("admin_barrier_view", args=[barrier.id])
        data = {"device_password": "0000"}

        response = authenticated_admin_client.put(url, data)

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.django_db
class TestBarrierLimitUpdateView:
    def test_update_limit_successfully(self, authenticated_admin_client, admin_user, barrier):
        url = reverse("update_barrier_limit", args=[barrier.id])
        data = {"sms_weekly_limit": 5}

        response = authenticated_admin_client.patch(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["sms_weekly_limit"] == 5
        assert barrier.limits.sms_weekly_limit == 5

    def test_update_limit_creates_if_missing(self, authenticated_admin_client, admin_user, barrier):
        url = reverse("update_barrier_limit", args=[barrier.id])
        data = {"user_phone_limit": 2}

        response = authenticated_admin_client.patch(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["user_phone_limit"] == 2
        assert BarrierLimit.objects.filter(barrier=barrier).exists()

    def test_update_limit_forbidden_for_non_owner(self, api_client, another_admin, barrier):
        api_client.force_authenticate(user=another_admin)
        url = reverse("update_barrier_limit", args=[barrier.id])
        data = {"user_temp_phone_limit": 3}

        response = api_client.patch(url, data)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["detail"] == "You are not the owner of this barrier."

    def test_update_limit_invalid_negative_value(self, authenticated_admin_client, admin_user, barrier):
        url = reverse("update_barrier_limit", args=[barrier.id])
        data = {"global_temp_phone_limit": -1}

        response = authenticated_admin_client.patch(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "global_temp_phone_limit" in response.data

    def test_put_method_not_allowed(self, authenticated_admin_client, admin_user, barrier):
        url = reverse("update_barrier_limit", args=[barrier.id])
        data = {"sms_weekly_limit": 7}

        response = authenticated_admin_client.put(url, data)

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.django_db
class TestAdminBarrierUsersListView:
    def test_admin_can_list_users_in_barrier(self, authenticated_admin_client, barrier, user, access_request):
        UserBarrier.create(user, barrier, access_request)
        response = authenticated_admin_client.get(reverse("barrier_users_list", args=[barrier.id]))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_count"] == 1
        assert response.data["users"][0]["id"] == user.id

    def test_users_are_sorted_by_full_name(self, authenticated_admin_client, barrier, create_access_request):
        user1 = User.objects.create(full_name="Z User", phone=USER_PHONE)
        user2 = User.objects.create(full_name="A User", phone=OTHER_PHONE)
        access_request1 = create_access_request(user1, barrier, status=AccessRequest.Status.ACCEPTED)
        access_request2 = create_access_request(user1, barrier, status=AccessRequest.Status.ACCEPTED)
        UserBarrier.objects.create(user=user1, barrier=barrier, access_request=access_request1, is_active=False)
        UserBarrier.objects.create(user=user2, barrier=barrier, access_request=access_request2)

        url = reverse("barrier_users_list", args=[barrier.id])
        response = authenticated_admin_client.get(f"{url}?ordering=full_name")

        assert response.status_code == status.HTTP_200_OK
        names = [user["full_name"] for user in response.data["users"]]
        assert names == sorted(names)

    def test_users_are_sorted_by_desc_phone(
        self, authenticated_admin_client, admin_user, barrier, create_access_request
    ):
        user1 = User.objects.create(full_name="User A", phone="+79991230001")
        user2 = User.objects.create(full_name="User B", phone="+79991230002")
        access_request1 = create_access_request(user1, barrier, status=AccessRequest.Status.ACCEPTED)
        access_request2 = create_access_request(user2, barrier, status=AccessRequest.Status.ACCEPTED)
        UserBarrier.create(user1, barrier, access_request1)
        UserBarrier.create(user2, barrier, access_request2)

        url = reverse("barrier_users_list", args=[barrier.id])
        response = authenticated_admin_client.get(f"{url}?ordering=-phone")

        assert response.status_code == status.HTTP_200_OK
        phones = [user["phone"] for user in response.data["users"]]
        assert phones == sorted(phones, reverse=True)

    def test_only_owner_can_list_users(self, authenticated_admin_client, another_admin, barrier):
        barrier.owner = another_admin
        barrier.save()
        url = reverse("barrier_users_list", args=[barrier.id])
        response = authenticated_admin_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["detail"] == "You are not the owner of this barrier."

    def test_inactive_users_not_listed(self, authenticated_admin_client, private_barrier_with_access, user):
        user.is_active = False
        user.save()
        url = reverse("barrier_users_list", args=[private_barrier_with_access.id])
        response = authenticated_admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_count"] == 0

    def test_user_with_inactive_barrier_access_not_listed(
        self, authenticated_admin_client, barrier, user, access_request
    ):
        UserBarrier.objects.create(user=user, barrier=barrier, access_request=access_request, is_active=False)
        url = reverse("barrier_users_list", args=[barrier.id])
        response = authenticated_admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_count"] == 0

    def test_users_not_listed_if_barrier_inactive(self, authenticated_admin_client, barrier, user, access_request):
        barrier.is_active = False
        barrier.save()
        UserBarrier.create(user, barrier, access_request)
        url = reverse("barrier_users_list", args=[barrier.id])
        response = authenticated_admin_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["detail"] == "Not found."


@pytest.mark.django_db
class TestAdminRemoveUserFromBarrierView:
    def test_admin_can_remove_user_from_barrier(self, authenticated_admin_client, barrier, user, access_request):
        user_barrier = UserBarrier.create(user, barrier, access_request)
        url = reverse("barrier_remove_user", kwargs={"barrier_id": barrier.id, "user_id": user.id})
        response = authenticated_admin_client.delete(url)

        assert response.status_code == status.HTTP_200_OK
        user_barrier.refresh_from_db()
        assert not user_barrier.is_active

    def test_user_inactive_returns_404(self, authenticated_admin_client, admin_user, barrier, user):
        user.is_active = False
        user.save()
        url = reverse("barrier_remove_user", kwargs={"barrier_id": barrier.id, "user_id": user.id})
        response = authenticated_admin_client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["detail"] == "Not found."

    def test_barrier_not_found_returns_404(self, authenticated_admin_client, admin_user, user):
        url = reverse("barrier_remove_user", kwargs={"barrier_id": 99999, "user_id": user.id})
        response = authenticated_admin_client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["detail"] == "Not found."

    def test_admin_cannot_remove_user_from_foreign_barrier(
        self, authenticated_admin_client, another_admin, user, barrier
    ):
        barrier.owner = another_admin
        barrier.save()
        url = reverse("barrier_remove_user", kwargs={"barrier_id": barrier.id, "user_id": user.id})
        response = authenticated_admin_client.delete(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["detail"] == "You are not the owner of this barrier."

    def test_remove_user_not_found(self, authenticated_admin_client, admin_user, barrier, user):
        url = reverse("barrier_remove_user", kwargs={"barrier_id": barrier.id, "user_id": user.id})
        response = authenticated_admin_client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["detail"] == "User not found in this barrier."
