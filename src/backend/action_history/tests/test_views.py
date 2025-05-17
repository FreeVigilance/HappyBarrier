from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils.timezone import now
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied

from action_history.models import BarrierActionLog
from action_history.views import get_barrier


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
        # No UserBarrier link created
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
class TestBarrierActionLogListViews:
    base_url = "user_action_history_list_view"
    base_url_admin = "admin_action_history_list_view"

    def get_url(self, barrier_id, *, as_admin=False, **params):
        base_url = self.base_url_admin if as_admin else self.base_url
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = reverse(base_url, kwargs={"id": barrier_id})
        return f"{url}?{query}" if query else url

    @pytest.mark.django_db
    class TestBarrierActionLogOrdering:
        base_url = "user_action_history_list_view"

        def get_url(self, barrier_id, *, ordering):
            return reverse(self.base_url, kwargs={"id": barrier_id}) + f"?ordering={ordering}"

        def test_valid_ordering_applied(
            self, authenticated_client, user, private_barrier_with_access, create_barrier_phone
        ):
            barrier = private_barrier_with_access
            phone_a, log_a = create_barrier_phone(user, barrier, phone="+70000000001", name="A")
            phone_z, log_z = create_barrier_phone(user, barrier, phone="+70000000002", name="Z")

            url = self.get_url(barrier.id, ordering="phone__phone")
            response = authenticated_client.get(url)
            assert response.status_code == status.HTTP_200_OK

            ids = [entry["id"] for entry in response.data["actions"]]
            assert ids.index(log_a.id) < ids.index(log_z.id)

        def test_invalid_ordering_uses_default(
            self, authenticated_client, user, private_barrier_with_access, create_barrier_phone
        ):
            barrier = private_barrier_with_access
            phone1, log1 = create_barrier_phone(user, barrier, phone="+70000000001", name="First")
            phone2, log2 = create_barrier_phone(user, barrier, phone="+70000000002", name="Second")

            url = self.get_url(barrier.id, ordering="non_existing_field")
            response = authenticated_client.get(url)
            assert response.status_code == status.HTTP_200_OK

            returned_ids = [entry["id"] for entry in response.data["actions"]]
            assert set(returned_ids) >= {log1.id, log2.id}

    def test_filter_by_phone_id(self, authenticated_admin_client, admin_user, barrier, create_barrier_phone):
        phone, log = create_barrier_phone(admin_user, barrier)
        url = self.get_url(barrier.id, as_admin=True, phone_id=phone.id)

        response = authenticated_admin_client.get(url)

        assert any(item["id"] == log.id for item in response.data["actions"])

    def test_filter_by_author(self, authenticated_admin_client, admin_user, barrier, create_barrier_phone):
        phone, _ = create_barrier_phone(admin_user, barrier)
        log = BarrierActionLog.objects.create(
            phone=phone,
            barrier=barrier,
            author=BarrierActionLog.Author.ADMIN,
            action_type=BarrierActionLog.ActionType.UPDATE_PHONE,
            reason=BarrierActionLog.Reason.MANUAL,
            new_value="Updated",
        )
        url = self.get_url(barrier.id, as_admin=True, author=BarrierActionLog.Author.ADMIN)
        response = authenticated_admin_client.get(url)
        assert any(item["id"] == log.id for item in response.data["actions"])

    def test_filter_by_action_type(self, authenticated_admin_client, admin_user, barrier, create_barrier_phone):
        phone, _ = create_barrier_phone(admin_user, barrier)
        log = BarrierActionLog.objects.create(
            phone=phone,
            barrier=barrier,
            author=BarrierActionLog.Author.SYSTEM,
            action_type=BarrierActionLog.ActionType.UPDATE_PHONE,
            reason=BarrierActionLog.Reason.MANUAL,
            new_value="Changed",
        )
        url = self.get_url(barrier.id, as_admin=True, action_type=BarrierActionLog.ActionType.UPDATE_PHONE)
        response = authenticated_admin_client.get(url)
        assert any(item["id"] == log.id for item in response.data["actions"])

    def test_filter_by_reason(self, authenticated_admin_client, admin_user, barrier, create_barrier_phone):
        phone, _ = create_barrier_phone(admin_user, barrier)
        log = BarrierActionLog.objects.create(
            phone=phone,
            barrier=barrier,
            author=BarrierActionLog.Author.SYSTEM,
            action_type=BarrierActionLog.ActionType.UPDATE_PHONE,
            reason=BarrierActionLog.Reason.SCHEDULE_UPDATE,
            new_value="Edited schedule",
        )
        url = self.get_url(barrier.id, as_admin=True, reason=BarrierActionLog.Reason.SCHEDULE_UPDATE)
        response = authenticated_admin_client.get(url)
        assert any(item["id"] == log.id for item in response.data["actions"])

    def test_filter_by_created_range(self, authenticated_admin_client, admin_user, barrier, create_barrier_phone):
        phone, _ = create_barrier_phone(admin_user, barrier)
        created_at = now() - timedelta(hours=1)
        log = BarrierActionLog.objects.create(
            phone=phone,
            barrier=barrier,
            author=BarrierActionLog.Author.SYSTEM,
            action_type=BarrierActionLog.ActionType.UPDATE_PHONE,
            reason=BarrierActionLog.Reason.MANUAL,
            created_at=created_at,
            new_value="Custom log",
        )
        from_ts = (created_at - timedelta(minutes=5)).isoformat()
        to_ts = (created_at + timedelta(minutes=5)).isoformat()
        url = self.get_url(barrier.id, as_admin=True, created_from=from_ts, created_to=to_ts)
        response = authenticated_admin_client.get(url)
        assert any(item["id"] == log.id for item in response.data["actions"])

    def test_filter_by_user_id(self, authenticated_admin_client, user, barrier, create_barrier_phone):
        phone, log = create_barrier_phone(user, barrier)
        url = self.get_url(barrier.id, as_admin=True, user=user.id)
        response = authenticated_admin_client.get(url)
        assert any(item["id"] == log.id for item in response.data["actions"])

    def test_invalid_user_id_returns_404(self, authenticated_admin_client, barrier):
        url = self.get_url(barrier.id, as_admin=True, user=999999)
        response = authenticated_admin_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["detail"] == "User not found."

    def test_invalid_phone_id_ignored(self, authenticated_admin_client, barrier):
        url = self.get_url(barrier.id, as_admin=True, phone_id="invalid")
        response = authenticated_admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_user_sees_only_own_logs(
        self, authenticated_client, user, another_user, private_barrier_with_access, create_barrier_phone
    ):
        barrier = private_barrier_with_access
        phone_own, log_own = create_barrier_phone(user, barrier, phone="+70000000001")
        phone_other, _ = create_barrier_phone(another_user, barrier, phone="+70000000002")

        url = self.get_url(barrier.id)
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        returned_ids = [item["id"] for item in response.data["actions"]]
        assert log_own.id in returned_ids
        assert all(log["id"] != phone_other.id for log in response.data["actions"])

    def test_user_filters_do_not_leak_data(
        self, authenticated_client, user, another_user, private_barrier_with_access, create_barrier_phone
    ):
        barrier = private_barrier_with_access
        create_barrier_phone(user, barrier, phone="+70000000001")
        phone_other, _ = create_barrier_phone(another_user, barrier, phone="+70000000002")

        url = self.get_url(barrier.id, user=another_user.id)
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        for log in response.data["actions"]:
            assert log["phone"] != phone_other.phone


@pytest.mark.django_db
class TestBarrierActionLogDetailViews:
    base_url = "user_action_history_detail_view"
    base_url_admin = "admin_action_history_detail_view"

    def get_url(self, log_id, *, as_admin=False):
        return reverse(self.base_url_admin if as_admin else self.base_url, kwargs={"id": log_id})

    def test_user_can_view_own_log(self, authenticated_client, user, private_barrier_with_access, create_barrier_phone):
        phone, log = create_barrier_phone(user, private_barrier_with_access)
        url = self.get_url(log.id)
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == log.id

    def test_user_cannot_view_foreign_log(
        self, authenticated_client, another_user, private_barrier_with_access, create_barrier_phone
    ):
        barrier = private_barrier_with_access
        phone, log = create_barrier_phone(user=another_user, barrier=barrier)
        url = self.get_url(log.id)
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_view_log_for_own_barrier(
        self, authenticated_admin_client, private_barrier_with_access, create_barrier_phone
    ):
        barrier = private_barrier_with_access
        phone, log = create_barrier_phone(user=authenticated_admin_client.handler._force_user, barrier=barrier)
        url = self.get_url(log.id, as_admin=True)
        response = authenticated_admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == log.id

    def test_admin_cannot_view_log_for_foreign_barrier(
        self, authenticated_admin_client, admin_user, another_admin, barrier, create_barrier_phone
    ):
        barrier.owner = another_admin
        barrier.save()
        phone, log = create_barrier_phone(admin_user, barrier)
        url = self.get_url(log.id, as_admin=True)
        response = authenticated_admin_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_user_cannot_view_log_without_phone(
        self, authenticated_client, user, private_barrier_with_access, create_barrier_phone
    ):
        barrier = private_barrier_with_access
        phone, log = create_barrier_phone(user, barrier)
        log.phone = None
        log.save()
        url = self.get_url(log.id)
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
