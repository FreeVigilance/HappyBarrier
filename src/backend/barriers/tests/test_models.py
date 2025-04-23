import pytest
from django.core.exceptions import PermissionDenied, ValidationError

from access_requests.models import AccessRequest
from barriers.models import BarrierLimit, UserBarrier


@pytest.mark.django_db
class TestBarrier:
    def test_delete_raises_permission_denied(self, barrier):
        """Test that delete() raises PermissionDenied."""

        with pytest.raises(Exception) as exc_info:
            barrier.delete()
        assert "not allowed" in str(exc_info.value)


@pytest.mark.django_db
class TestUserBarrier:
    class TestUserBarrierCreate:
        def test_creates_new_active_link(self, user, barrier, access_request):
            user_barrier = UserBarrier.create(user, barrier, access_request)

            assert user_barrier.user == user
            assert user_barrier.barrier == barrier
            assert user_barrier.access_request == access_request
            assert user_barrier.is_active is True

        def test_raises_error_if_no_access_request(self, user, barrier):
            with pytest.raises(ValidationError, match="Access request is required to create a user-barrier link."):
                UserBarrier.create(user, barrier, None)

        def test_raises_error_if_invalid_access_request(self, admin_user, barrier, access_request):
            with pytest.raises(ValidationError, match="Access request does not match given user and barrier."):
                UserBarrier.create(admin_user, barrier, access_request)

        def test_reactivates_existing_inactive_link(self, user, barrier, create_access_request):
            old_access_request = create_access_request(user, barrier, status=AccessRequest.Status.ACCEPTED)
            new_access_request = create_access_request(user, barrier, status=AccessRequest.Status.ACCEPTED)

            user_barrier = UserBarrier.objects.create(
                user=user, barrier=barrier, access_request=old_access_request, is_active=False
            )

            result = UserBarrier.create(user, barrier, new_access_request)

            user_barrier.refresh_from_db()
            assert result == user_barrier
            assert user_barrier.is_active is True
            assert user_barrier.access_request == new_access_request

        def test_raises_error_if_active_link_exists(self, user, barrier, access_request):
            UserBarrier.create(user, barrier, access_request)

            with pytest.raises(ValidationError, match="An active access already exists for this user and barrier."):
                UserBarrier.create(user, barrier, access_request)

    class TestUserHasAccessToBarrier:
        def test_returns_true(self, user, barrier, access_request):
            UserBarrier.create(user, barrier, access_request)

            result = UserBarrier.user_has_access_to_barrier(user, barrier)

            assert result is True

        def test_returns_false_if_no_link(self, user, barrier):
            result = UserBarrier.user_has_access_to_barrier(user, barrier)

            assert result is False

        def test_returns_false_if_inactive(self, user, barrier, access_request):
            UserBarrier.objects.create(user=user, barrier=barrier, access_request=access_request, is_active=False)

            result = UserBarrier.user_has_access_to_barrier(user, barrier)

            assert result is False

    def test_delete_raises_permission_denied(self, barrier):
        """Test that delete() raises PermissionDenied."""

        with pytest.raises(Exception) as exc_info:
            barrier.delete()
        assert "not allowed" in str(exc_info.value)


@pytest.mark.django_db
class TestBarrierLimit:
    def test_creation_with_all_fields(self, user, barrier):
        limits = BarrierLimit.objects.create(
            barrier=barrier,
            user_phone_limit=3,
            user_temp_phone_limit=2,
            global_temp_phone_limit=10,
            sms_weekly_limit=100,
        )

        assert limits.barrier == barrier
        assert limits.user_phone_limit == 3
        assert limits.user_temp_phone_limit == 2
        assert limits.global_temp_phone_limit == 10
        assert limits.sms_weekly_limit == 100

    def test_str_method_with_limits(self, barrier):
        """Should correctly format string with some limits"""

        limits = BarrierLimit.objects.create(
            barrier=barrier,
            user_phone_limit=3,
            sms_weekly_limit=10,
        )

        expected = f"Limits for Barrier '{barrier.address}' (ID: {barrier.id}) — [user_phones: 3, sms_in_week: 10]"
        assert str(limits) == expected

    def test_str_method_with_no_limits(self, barrier):
        """Should return empty brackets if no limits provided"""
        limits = BarrierLimit.objects.create(barrier=barrier)

        expected = f"Limits for Barrier '{barrier.address}' (ID: {barrier.id}) — []"
        assert str(limits) == expected

    def test_delete_raises_permission_denied(self, barrier):
        limit = BarrierLimit.objects.create(barrier=barrier, user_phone_limit=10)

        with pytest.raises(PermissionDenied):
            limit.delete()
