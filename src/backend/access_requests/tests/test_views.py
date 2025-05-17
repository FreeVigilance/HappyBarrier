import json
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework import status

from access_requests.models import AccessRequest
from action_history.models import BarrierActionLog
from barriers.models import UserBarrier
from phones.models import BarrierPhone


@pytest.mark.django_db
class TestCreateAccessRequestView:
    url = reverse("create_access_request")
    admin_url = reverse("admin_create_access_request")

    def test_user_creates_access_request(self, authenticated_client, barrier, user):
        response = authenticated_client.post(self.url, data={"user": user.id, "barrier": barrier.id})

        assert response.status_code == status.HTTP_201_CREATED
        assert AccessRequest.objects.filter(user=user, barrier=barrier).exists()

    def test_barrier_not_found(self, authenticated_client, user):
        response = authenticated_client.post(self.url, data={"user": user.id, "barrier": 999999})

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["detail"] == "Barrier not found."

    def test_user_cannot_create_for_another_user(self, authenticated_client, barrier, admin_user):
        response = authenticated_client.post(self.url, data={"user": admin_user.id, "barrier": barrier.id})

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["detail"] == "You cannot create access request for other user."

    def test_user_cannot_request_private_barrier(self, authenticated_client, private_barrier, user):
        response = authenticated_client.post(self.url, data={"user": user.id, "barrier": private_barrier.id})

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["detail"] == "Barrier not found."

    def test_cannot_create_duplicate_request(self, authenticated_client, barrier, user):
        AccessRequest.objects.create(user=user, barrier=barrier, status=AccessRequest.Status.PENDING)
        response = authenticated_client.post(self.url, data={"user": user.id, "barrier": barrier.id})

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data["detail"] == "An active access request already exists for this user and barrier."

    def test_cannot_create_if_user_has_access(self, authenticated_client, user, barrier, access_request):
        UserBarrier.objects.create(user=user, barrier=barrier, access_request=access_request)
        response = authenticated_client.post(self.url, data={"user": user.id, "barrier": barrier.id})

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data["detail"] == "This user already has access to the barrier."

    def test_admin_creates_access_request(self, authenticated_admin_client, admin_user, user, barrier):
        response = authenticated_admin_client.post(self.admin_url, data={"user": user.id, "barrier": barrier.id})

        assert response.status_code == status.HTTP_201_CREATED

    def test_user_not_found(self, authenticated_admin_client, barrier):
        response = authenticated_admin_client.post(self.admin_url, data={"user": 999999, "barrier": barrier.id})

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["detail"] == "User not found."

    def test_admin_cannot_create_request_for_foreign_barrier(self, authenticated_admin_client, other_barrier, user):
        data = {"user": user.id, "barrier": other_barrier.id}
        response = authenticated_admin_client.post(self.admin_url, data=data)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["detail"] == "You do not have access to this barrier."


@pytest.mark.django_db
class TestAccessRequestListViews:
    url = reverse("my_access_requests")
    admin_url = reverse("admin_access_requests")

    def test_user_sees_own_requests(self, authenticated_client, user, barrier):
        AccessRequest.objects.create(
            user=user,
            barrier=barrier,
            request_type=AccessRequest.RequestType.FROM_USER,
            status=AccessRequest.Status.PENDING,
        )
        response = authenticated_client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["access_requests"]

    def test_admin_sees_requests_for_their_barriers(self, authenticated_admin_client, admin_user, user, barrier):
        AccessRequest.objects.create(
            user=user,
            barrier=barrier,
            request_type=AccessRequest.RequestType.FROM_USER,
            status=AccessRequest.Status.PENDING,
        )
        response = authenticated_admin_client.get(self.admin_url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["access_requests"]


@pytest.mark.django_db
class TestAccessRequestDetailView:
    base_url = "access_request_view"
    base_url_admin = "admin_access_request_view"

    @pytest.fixture
    def user_access_request(self, user, barrier, create_access_request):
        return create_access_request(user, barrier, AccessRequest.RequestType.FROM_USER)

    @pytest.fixture
    def admin_access_request(self, user, barrier, create_access_request):
        return create_access_request(user, barrier, AccessRequest.RequestType.FROM_BARRIER)

    def test_user_cannot_access_others_request(self, authenticated_client, admin_user, barrier, create_access_request):
        access_request = create_access_request(user=admin_user, barrier=barrier)
        response = authenticated_client.get(reverse(self.base_url, args=[access_request.id]))

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["detail"] == "You do not have access to this access request."

    def test_admin_cannot_access_request_for_foreign_barrier(
        self, authenticated_admin_client, another_admin, user, barrier, create_access_request
    ):
        barrier.owner = another_admin
        barrier.save()
        access_request = create_access_request(user, barrier)

        response = authenticated_admin_client.get(reverse(self.base_url_admin, args=[access_request.id]))

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["detail"] == "You do not have access to this access request."

    def test_user_cannot_access_cancelled_request_created_by_admin(
        self, authenticated_client, user, barrier, create_access_request
    ):
        access_request = create_access_request(
            user, barrier, AccessRequest.RequestType.FROM_BARRIER, AccessRequest.Status.CANCELLED
        )
        response = authenticated_client.get(reverse(self.base_url, args=[access_request.id]))

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["detail"] == "You do not have access to this access request."

    def test_admin_cannot_access_cancelled_request_created_by_user(
        self, authenticated_admin_client, user, barrier, create_access_request
    ):
        access_request = create_access_request(user, barrier, status=AccessRequest.Status.CANCELLED)
        response = authenticated_admin_client.get(reverse(self.base_url_admin, args=[access_request.id]))

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["detail"] == "You do not have access to this access request."

    def test_user_can_cancel_own_request(self, authenticated_client, user_access_request):
        url = reverse(self.base_url, args=[user_access_request.id])
        data = json.dumps({"status": AccessRequest.Status.CANCELLED})
        response = authenticated_client.patch(url, data=data, content_type="application/json")

        assert response.status_code == status.HTTP_200_OK
        user_access_request.refresh_from_db()
        assert user_access_request.status == AccessRequest.Status.CANCELLED

    def test_user_cannot_cancel_request_created_by_admin(self, authenticated_client, admin_access_request):
        url = reverse(self.base_url, args=[admin_access_request.id])
        data = json.dumps({"status": AccessRequest.Status.CANCELLED})
        response = authenticated_client.patch(url, data=data, content_type="application/json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["detail"] == "You are not allowed to cancel this request."

    @patch.object(BarrierPhone, "send_sms_to_create")
    def test_user_can_accept_admin_request(
        self, mock_send_sms_to_create, authenticated_client, user, barrier, admin_access_request
    ):
        url = reverse(self.base_url, args=[admin_access_request.id])
        data = json.dumps({"status": AccessRequest.Status.ACCEPTED})
        response = authenticated_client.patch(url, data=data, content_type="application/json")

        assert response.status_code == status.HTTP_200_OK
        admin_access_request.refresh_from_db()
        assert admin_access_request.status == AccessRequest.Status.ACCEPTED
        assert UserBarrier.objects.filter(user=user, barrier=barrier, is_active=True).exists()

        phone = BarrierPhone.objects.get(user=user, barrier=barrier, type=BarrierPhone.PhoneType.PRIMARY)
        assert phone.phone == user.phone

        log = BarrierActionLog.objects.get(
            phone=phone,
            action_type=BarrierActionLog.ActionType.ADD_PHONE,
            reason=BarrierActionLog.Reason.ACCESS_GRANTED,
        )

        assert log is not None
        assert log.author == BarrierActionLog.Author.SYSTEM
        assert log.new_value == phone.describe_phone_params()

        mock_send_sms_to_create.assert_called_once_with(log)

    def test_user_cannot_reject_own_request(self, authenticated_client, user_access_request):
        url = reverse(self.base_url, args=[user_access_request.id])
        data = json.dumps({"status": AccessRequest.Status.REJECTED})
        response = authenticated_client.patch(url, data=data, content_type="application/json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["detail"] == "You are not allowed to accept or reject this request."

    def test_admin_can_cancel_own_request(self, authenticated_admin_client, admin_access_request):
        url = reverse(self.base_url_admin, args=[admin_access_request.id])
        data = json.dumps({"status": AccessRequest.Status.CANCELLED})
        response = authenticated_admin_client.patch(url, data=data, content_type="application/json")

        assert response.status_code == status.HTTP_200_OK
        admin_access_request.refresh_from_db()
        assert admin_access_request.status == AccessRequest.Status.CANCELLED

    def test_admin_cannot_cancel_request_created_by_user(self, authenticated_admin_client, user_access_request):
        url = reverse(self.base_url_admin, args=[user_access_request.id])
        data = json.dumps({"status": AccessRequest.Status.CANCELLED})
        response = authenticated_admin_client.patch(url, data=data, content_type="application/json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["detail"] == "You are not allowed to cancel this request."

    @patch.object(BarrierPhone, "send_sms_to_create")
    def test_admin_can_accept_user_request(
        self, mock_send_sms_to_create, authenticated_admin_client, user, barrier, user_access_request
    ):
        url = reverse(self.base_url_admin, args=[user_access_request.id])
        data = json.dumps({"status": AccessRequest.Status.ACCEPTED})
        response = authenticated_admin_client.patch(url, data=data, content_type="application/json")

        assert response.status_code == status.HTTP_200_OK
        user_access_request.refresh_from_db()
        assert user_access_request.status == AccessRequest.Status.ACCEPTED
        assert UserBarrier.objects.filter(user=user, barrier=barrier, is_active=True).exists()

        phone = BarrierPhone.objects.get(user=user, barrier=barrier, type=BarrierPhone.PhoneType.PRIMARY)
        assert phone.phone == user.phone

        log = BarrierActionLog.objects.get(
            phone=phone,
            action_type=BarrierActionLog.ActionType.ADD_PHONE,
            reason=BarrierActionLog.Reason.ACCESS_GRANTED,
        )

        assert log is not None
        assert log.author == BarrierActionLog.Author.SYSTEM
        assert log.new_value == phone.describe_phone_params()

        mock_send_sms_to_create.assert_called_once_with(log)

    def test_admin_cannot_accept_own_request(self, authenticated_admin_client, admin_access_request):
        url = reverse(self.base_url_admin, args=[admin_access_request.id])
        data = json.dumps({"status": AccessRequest.Status.ACCEPTED})
        response = authenticated_admin_client.patch(url, data=data, content_type="application/json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["detail"] == "You are not allowed to accept or reject this request."

    def test_put_method_not_allowed(self, authenticated_client, user, barrier, access_request):
        url = reverse("access_request_view", args=[access_request.id])
        response = authenticated_client.put(url, data={})

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert response.data["detail"].lower() == 'method "put" not allowed.'
