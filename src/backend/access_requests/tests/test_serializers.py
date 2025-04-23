import pytest

from access_requests.models import AccessRequest
from access_requests.serializers import CreateAccessRequestSerializer, UpdateAccessRequestSerializer
from barriers.models import UserBarrier


@pytest.mark.django_db
class TestCreateAccessRequestSerializer:
    def test_user_creates_valid_request(self, user, barrier):
        context = {"request": type("Request", (), {"user": user})(), "as_admin": False}
        data = {"user": user.id, "barrier": barrier.id}
        serializer = CreateAccessRequestSerializer(data=data, context=context)

        assert serializer.is_valid(), serializer.errors

    def test_user_cannot_request_private_barrier(self, user, private_barrier):
        context = {"request": type("Request", (), {"user": user})(), "as_admin": False}
        data = {"user": user.id, "barrier": private_barrier.id}
        serializer = CreateAccessRequestSerializer(data=data, context=context)

        assert not serializer.is_valid()
        assert serializer.errors["error"][0] == "Cannot request access to a private barrier."

    def test_user_cannot_create_for_another_user(self, user, admin_user, barrier):
        context = {"request": type("Request", (), {"user": user})(), "as_admin": False}
        data = {"user": admin_user.id, "barrier": barrier.id}
        serializer = CreateAccessRequestSerializer(data=data, context=context)

        assert not serializer.is_valid()
        assert serializer.errors["error"][0] == "Users can only create requests for themselves."

    def test_admin_creates_valid_request(self, admin_user, user, barrier):
        context = {"request": type("Request", (), {"user": admin_user})(), "as_admin": True}
        data = {"user": user.id, "barrier": barrier.id}
        serializer = CreateAccessRequestSerializer(data=data, context=context)

        assert serializer.is_valid(), serializer.errors

    def test_admin_cannot_create_for_barrier_they_do_not_own(self, user, barrier, another_admin):
        context = {"request": type("Request", (), {"user": another_admin})(), "as_admin": True}
        data = {"user": user.id, "barrier": barrier.id}
        serializer = CreateAccessRequestSerializer(data=data, context=context)

        assert not serializer.is_valid()
        assert serializer.errors["error"][0] == "You are not the owner of this barrier."

    def test_cannot_create_if_pending_request_exists(self, user, barrier):
        AccessRequest.objects.create(user=user, barrier=barrier, status=AccessRequest.Status.PENDING)

        context = {"request": type("Request", (), {"user": user})(), "as_admin": False}
        data = {"user": user.id, "barrier": barrier.id}
        serializer = CreateAccessRequestSerializer(data=data, context=context)

        assert not serializer.is_valid()
        assert serializer.errors["error"][0] == "An active request already exists for this user and barrier."

    @pytest.fixture
    def public_barrier_with_access(self, user, barrier, access_request):
        """Private barrier to which the user has access"""

        UserBarrier.objects.create(user=user, barrier=barrier, access_request=access_request)
        return barrier

    def test_cannot_create_if_user_already_has_access(self, user, public_barrier_with_access):
        context = {"request": type("Request", (), {"user": user})(), "as_admin": False}
        data = {"user": user.id, "barrier": public_barrier_with_access.id}
        serializer = CreateAccessRequestSerializer(data=data, context=context)

        assert not serializer.is_valid()
        assert serializer.errors["error"][0] == "This user already has access to the barrier."


@pytest.mark.django_db
class TestUpdateAccessRequestSerializer:
    def test_valid_cancel_by_user(self, user, barrier):
        access_request = AccessRequest.objects.create(
            user=user,
            barrier=barrier,
            request_type=AccessRequest.RequestType.FROM_USER,
            status=AccessRequest.Status.PENDING,
        )
        context = {"as_admin": False}
        data = {"status": AccessRequest.Status.CANCELLED}
        serializer = UpdateAccessRequestSerializer(access_request, data=data, partial=True, context=context)

        assert serializer.is_valid(), serializer.errors

    def test_invalid_status_transition(self, user, barrier):
        access_request = AccessRequest.objects.create(
            user=user,
            barrier=barrier,
            request_type=AccessRequest.RequestType.FROM_USER,
            status=AccessRequest.Status.ACCEPTED,
        )
        context = {"as_admin": False}
        data = {"status": AccessRequest.Status.CANCELLED}
        serializer = UpdateAccessRequestSerializer(access_request, data=data, partial=True, context=context)

        assert not serializer.is_valid()
        assert serializer.errors["error"][0] == "Invalid status transition: accepted -> cancelled"

    def test_user_cannot_accept_request(self, user, barrier):
        access_request = AccessRequest.objects.create(
            user=user,
            barrier=barrier,
            request_type=AccessRequest.RequestType.FROM_USER,
            status=AccessRequest.Status.PENDING,
        )
        context = {"as_admin": False}
        data = {"status": AccessRequest.Status.ACCEPTED}
        serializer = UpdateAccessRequestSerializer(access_request, data=data, partial=True, context=context)

        assert not serializer.is_valid()
        assert serializer.errors["error"][0] == "You are not allowed to accept or reject this request."

    def test_admin_can_accept_user_request(self, user, admin_user, barrier):
        access_request = AccessRequest.objects.create(
            user=user,
            barrier=barrier,
            request_type=AccessRequest.RequestType.FROM_USER,
            status=AccessRequest.Status.PENDING,
        )
        context = {"as_admin": True}
        data = {"status": AccessRequest.Status.ACCEPTED}
        serializer = UpdateAccessRequestSerializer(access_request, data=data, partial=True, context=context)

        assert serializer.is_valid(), serializer.errors

    def test_user_cannot_change_hidden_for_admin(self, user, barrier):
        access_request = AccessRequest.objects.create(
            user=user,
            barrier=barrier,
            request_type=AccessRequest.RequestType.FROM_USER,
        )
        context = {"as_admin": False}
        data = {"hidden_for_admin": True}
        serializer = UpdateAccessRequestSerializer(access_request, data=data, partial=True, context=context)

        assert not serializer.is_valid()
        assert serializer.errors["error"][0] == "Only admins can modify field 'hidden_for_admin'."

    def test_admin_cannot_change_hidden_for_user(self, user, barrier):
        access_request = AccessRequest.objects.create(
            user=user,
            barrier=barrier,
            request_type=AccessRequest.RequestType.FROM_USER,
        )
        context = {"as_admin": True}
        data = {"hidden_for_user": True}
        serializer = UpdateAccessRequestSerializer(access_request, data=data, partial=True, context=context)

        assert not serializer.is_valid()
        assert serializer.errors["error"][0] == "Only users can modify field 'hidden_for_user'."
