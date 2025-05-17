from datetime import timedelta
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils.timezone import now
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied

from message_management.models import SMSMessage
from message_management.views import get_barrier


@pytest.mark.django_db
class TestGetBarrier:
    def test_returns_barrier_for_user_with_access(self, user, private_barrier_with_access):
        barrier = private_barrier_with_access
        result = get_barrier(user, barrier.id, as_admin=False)
        assert result == barrier

    def test_returns_barrier_for_admin_owner(self, admin_user, barrier):
        barrier.owner = admin_user
        barrier.save()
        result = get_barrier(admin_user, barrier.id, as_admin=True)
        assert result == barrier

    def test_raises_not_found_if_barrier_does_not_exist(self, user):
        with pytest.raises(NotFound) as exc:
            get_barrier(user, 999999, as_admin=False)
        assert str(exc.value.detail) == "Barrier not found."

    def test_user_without_access_raises_permission_denied(self, user, barrier):
        with pytest.raises(PermissionDenied) as exc:
            get_barrier(user, barrier.id, as_admin=False)
        assert str(exc.value) == "You do not have access to this barrier."

    def test_admin_not_owner_raises_permission_denied(self, admin_user, barrier, another_admin):
        barrier.owner = another_admin
        barrier.save()
        with pytest.raises(PermissionDenied) as exc:
            get_barrier(admin_user, barrier.id, as_admin=True)
        assert str(exc.value) == "You do not have access to this barrier."


@pytest.mark.django_db
class TestSMSMessageListViews:
    base_url = "user_sms_list"
    base_url_admin = "admin_sms_list"

    def get_url(self, barrier_id, *, as_admin=False, **params):
        base_url = self.base_url_admin if as_admin else self.base_url
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = reverse(base_url, kwargs={"id": barrier_id})
        return f"{url}?{query}" if query else url

    def test_user_sees_only_own_sms(
        self, authenticated_client, user, private_barrier_with_access, create_barrier_phone
    ):
        phone, log = create_barrier_phone(user, private_barrier_with_access)
        visible = SMSMessage.objects.create(
            phone=phone.phone, message_type=SMSMessage.MessageType.PHONE_COMMAND, log=log
        )
        SMSMessage.objects.create(phone=phone.phone, message_type=SMSMessage.MessageType.VERIFICATION_CODE, log=log)
        SMSMessage.objects.create(phone=phone.phone, message_type=SMSMessage.MessageType.BARRIER_SETTING, log=log)

        url = self.get_url(private_barrier_with_access.id)
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data["sms"]]
        assert visible.id in ids
        assert len(ids) == 1

    def test_admin_can_see_all_except_verification(
        self, authenticated_admin_client, admin_user, barrier, create_barrier_phone
    ):
        phone, log = create_barrier_phone(admin_user, barrier)

        visible = SMSMessage.objects.create(
            phone=phone.phone, message_type=SMSMessage.MessageType.BARRIER_SETTING, log=log
        )
        hidden = SMSMessage.objects.create(
            phone=phone.phone, message_type=SMSMessage.MessageType.VERIFICATION_CODE, log=log
        )

        url = self.get_url(barrier.id, as_admin=True)
        response = authenticated_admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data["sms"]]
        assert visible.id in ids
        assert hidden.id not in ids

    def test_ordering_applied(self, authenticated_admin_client, admin_user, barrier, create_barrier_phone):
        phone, log = create_barrier_phone(admin_user, barrier)
        SMSMessage.objects.create(phone=phone.phone, message_type=SMSMessage.MessageType.PHONE_COMMAND, log=log)
        sms2 = SMSMessage.objects.create(phone=phone.phone, message_type=SMSMessage.MessageType.PHONE_COMMAND, log=log)
        sms2.updated_at = now() + timedelta(minutes=1)
        sms2.save()

        url = self.get_url(barrier.id, as_admin=True, ordering="-updated_at")
        response = authenticated_admin_client.get(url)
        ids = [sms["id"] for sms in response.data["sms"]]
        assert ids == sorted(ids, reverse=True)

    def test_filter_by_phone_id(self, authenticated_admin_client, admin_user, barrier, create_barrier_phone):
        phone, _ = create_barrier_phone(admin_user, barrier)
        url = self.get_url(barrier.id, as_admin=True, phone_id=phone.id)
        response = authenticated_admin_client.get(url)
        assert response.status_code == 200

    def test_filter_by_log_id(self, authenticated_admin_client, admin_user, barrier, create_barrier_phone):
        phone, log = create_barrier_phone(admin_user, barrier)
        sms = SMSMessage.objects.create(phone=phone.phone, message_type=SMSMessage.MessageType.PHONE_COMMAND, log=log)

        url = self.get_url(barrier.id, as_admin=True, log=log.id)
        response = authenticated_admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert any(item["id"] == sms.id for item in response.data["sms"])

    def test_invalid_log_id_ignored(self, authenticated_admin_client, barrier):
        url = self.get_url(barrier.id, as_admin=True, log="invalid")
        response = authenticated_admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_filters_by_message_type(self, authenticated_admin_client, admin_user, barrier, create_barrier_phone):
        phone, log = create_barrier_phone(admin_user, barrier)
        sms = SMSMessage.objects.create(phone=phone.phone, message_type=SMSMessage.MessageType.PHONE_COMMAND, log=log)

        url = self.get_url(barrier.id, as_admin=True, message_type=SMSMessage.MessageType.PHONE_COMMAND)
        response = authenticated_admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert any(item["id"] == sms.id for item in response.data["sms"])

    def test_user_sms_filtered_by_type(
        self, authenticated_client, user, private_barrier_with_access, create_barrier_phone
    ):
        phone, log = create_barrier_phone(user, private_barrier_with_access)
        sms_visible = SMSMessage.objects.create(
            phone=phone.phone, message_type=SMSMessage.MessageType.PHONE_COMMAND, log=log
        )
        SMSMessage.objects.create(phone=phone.phone, message_type=SMSMessage.MessageType.VERIFICATION_CODE, log=log)

        url = self.get_url(private_barrier_with_access.id)
        response = authenticated_client.get(url)

        ids = [sms["id"] for sms in response.data["sms"]]
        assert sms_visible.id in ids

    def test_filter_by_sent_and_updated_ranges(
        self, authenticated_admin_client, admin_user, barrier, create_barrier_phone
    ):
        phone, log = create_barrier_phone(admin_user, barrier)
        past_time = now() - timedelta(days=1)
        future_time = now() + timedelta(days=1)

        sms = SMSMessage.objects.create(phone=phone.phone, message_type=SMSMessage.MessageType.PHONE_COMMAND, log=log)
        sms.sent_at = now()
        sms.updated_at = now()
        sms.save()

        url = self.get_url(
            barrier.id,
            as_admin=True,
            sent_from=past_time.isoformat(),
            sent_to=future_time.isoformat(),
            updated_from=past_time.isoformat(),
            updated_to=future_time.isoformat(),
        )
        response = authenticated_admin_client.get(url)
        assert sms.id in [s["id"] for s in response.data["sms"]]


@pytest.mark.django_db
class TestSMSMessageDetailViews:
    base_url = "user_sms_detail"
    base_url_admin = "admin_sms_detail"

    def get_url(self, sms_id, *, as_admin=False):
        return reverse(self.base_url_admin if as_admin else self.base_url, kwargs={"id": sms_id})

    def test_user_can_view_own_sms(self, authenticated_client, user, private_barrier_with_access, create_barrier_phone):
        phone, log = create_barrier_phone(user, private_barrier_with_access)
        sms = SMSMessage.objects.create(message_type=SMSMessage.MessageType.PHONE_COMMAND, phone=phone.phone, log=log)

        url = self.get_url(sms.id)
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == sms.id

    def test_user_cannot_view_barrier_setting_sms(
        self, authenticated_client, user, private_barrier_with_access, create_barrier_phone
    ):
        phone, log = create_barrier_phone(user, private_barrier_with_access)
        sms = SMSMessage.objects.create(message_type=SMSMessage.MessageType.BARRIER_SETTING, phone=phone.phone, log=log)

        url = self.get_url(sms.id)
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_user_cannot_view_foreign_sms(
        self, authenticated_client, another_user, private_barrier_with_access, create_barrier_phone
    ):
        phone, log = create_barrier_phone(another_user, private_barrier_with_access)
        sms = SMSMessage.objects.create(message_type=SMSMessage.MessageType.PHONE_COMMAND, phone=phone.phone, log=log)

        url = self.get_url(sms.id)
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_user_cannot_view_sms_with_no_log(self, authenticated_client, user):
        sms = SMSMessage.objects.create(message_type=SMSMessage.MessageType.PHONE_COMMAND, phone=user.phone)

        url = self.get_url(sms.id)
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_admin_can_view_sms_on_own_barrier(
        self, authenticated_admin_client, admin_user, barrier, create_barrier_phone
    ):
        barrier.owner = admin_user
        barrier.save()
        phone, log = create_barrier_phone(admin_user, barrier)
        sms = SMSMessage.objects.create(message_type=SMSMessage.MessageType.BARRIER_SETTING, phone=phone.phone, log=log)

        url = self.get_url(sms.id, as_admin=True)
        response = authenticated_admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == sms.id

    def test_admin_cannot_view_sms_on_foreign_barrier(
        self, authenticated_admin_client, admin_user, barrier, another_admin, create_barrier_phone
    ):
        barrier.owner = another_admin
        barrier.save()
        phone, log = create_barrier_phone(admin_user, barrier)
        sms = SMSMessage.objects.create(message_type=SMSMessage.MessageType.BARRIER_SETTING, phone=phone.phone, log=log)

        url = self.get_url(sms.id, as_admin=True)
        response = authenticated_admin_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestRetrySMSMessageView:
    def get_url(self, sms_id, *, as_admin=False):
        if as_admin:
            return reverse("admin_sms_retry", kwargs={"id": sms_id})
        return reverse("user_sms_retry", kwargs={"id": sms_id})

    @patch("message_management.services.send_sms_to_kafka")
    def test_retry_sms_success_for_admin(self, mock_send, authenticated_admin_client, barrier, create_barrier_phone):
        from message_management.models import SMSMessage

        phone, log = create_barrier_phone(barrier.owner, barrier)
        sms = SMSMessage.objects.create(
            message_type=SMSMessage.MessageType.PHONE_COMMAND,
            phone=phone.phone,
            log=log,
            status=SMSMessage.Status.FAILED,
            sent_at=now(),
        )
        url = self.get_url(sms.id, as_admin=True)
        response = authenticated_admin_client.post(url)
        assert response.status_code == 200
        assert response.data["new_sms_id"] != sms.id

    def test_retry_sms_not_found(self, authenticated_admin_client):
        url = reverse("admin_sms_retry", kwargs={"id": 999999})
        response = authenticated_admin_client.post(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_cannot_retry_non_failed_sms(self, authenticated_admin_client, barrier, create_barrier_phone):
        from message_management.models import SMSMessage

        phone, log = create_barrier_phone(barrier.owner, barrier)
        sms = SMSMessage.objects.create(
            message_type=SMSMessage.MessageType.PHONE_COMMAND,
            phone=phone.phone,
            log=log,
            status=SMSMessage.Status.SENT,
            sent_at=now(),
        )
        url = self.get_url(sms.id, as_admin=True)
        response = authenticated_admin_client.post(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cannot_retry_old_sms(self, authenticated_admin_client, barrier, create_barrier_phone):
        from message_management.models import SMSMessage

        phone, log = create_barrier_phone(barrier.owner, barrier)
        sms = SMSMessage.objects.create(
            message_type=SMSMessage.MessageType.PHONE_COMMAND,
            phone=phone.phone,
            log=log,
            status=SMSMessage.Status.FAILED,
        )
        sms.sent_at = now() - timedelta(days=3)
        sms.save(update_fields=["sent_at"])
        url = self.get_url(sms.id, as_admin=True)
        response = authenticated_admin_client.post(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_user_cannot_retry_foreign_sms(
        self, authenticated_client, another_user, private_barrier_with_access, create_barrier_phone
    ):
        phone, log = create_barrier_phone(another_user, private_barrier_with_access)
        sms = SMSMessage.objects.create(
            message_type=SMSMessage.MessageType.PHONE_COMMAND,
            phone=phone.phone,
            log=log,
            status=SMSMessage.Status.FAILED,
            sent_at=now(),
        )
        url = self.get_url(sms.id)
        response = authenticated_client.post(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_user_cannot_retry_barrier_setting_sms(
        self, authenticated_client, user, private_barrier_with_access, create_barrier_phone
    ):
        phone, log = create_barrier_phone(user, private_barrier_with_access)
        sms = SMSMessage.objects.create(
            message_type=SMSMessage.MessageType.BARRIER_SETTING,
            phone=phone.phone,
            log=log,
            status=SMSMessage.Status.FAILED,
            sent_at=now(),
        )
        url = self.get_url(sms.id)
        response = authenticated_client.post(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_cannot_retry_sms_on_foreign_barrier(
        self, authenticated_admin_client, barrier, another_admin, create_barrier_phone
    ):
        barrier.owner = another_admin
        barrier.save()
        phone, log = create_barrier_phone(barrier.owner, barrier)
        sms = SMSMessage.objects.create(
            message_type=SMSMessage.MessageType.PHONE_COMMAND,
            phone=phone.phone,
            log=log,
            status=SMSMessage.Status.FAILED,
            sent_at=now(),
        )
        url = self.get_url(sms.id, as_admin=True)
        response = authenticated_admin_client.post(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cannot_retry_sms_too_soon_after_previous(self, authenticated_admin_client, barrier, create_barrier_phone):
        from message_management.models import SMSMessage

        phone, log = create_barrier_phone(barrier.owner, barrier)

        SMSMessage.objects.create(
            message_type=SMSMessage.MessageType.PHONE_COMMAND,
            phone=phone.phone,
            log=log,
            status=SMSMessage.Status.SENT,
            sent_at=now() - timedelta(minutes=5),
        )

        failed_sms = SMSMessage.objects.create(
            message_type=SMSMessage.MessageType.PHONE_COMMAND,
            phone=phone.phone,
            log=log,
            status=SMSMessage.Status.FAILED,
            sent_at=now() - timedelta(minutes=20),
        )

        url = self.get_url(failed_sms.id, as_admin=True)
        response = authenticated_admin_client.post(url)
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "already sent recently" in response.data["detail"]
