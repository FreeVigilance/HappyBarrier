import pytest
from django.core.exceptions import PermissionDenied

from access_requests.models import AccessRequest


@pytest.mark.django_db
class TestAccessRequestModel:
    def test_str_from_user(self, user, barrier):
        request = AccessRequest.objects.create(
            user=user,
            barrier=barrier,
            request_type=AccessRequest.RequestType.FROM_USER,
        )
        assert str(request) == f"`{user}` -> `{barrier}` [{request.status}]"

    def test_str_from_barrier(self, user, barrier):
        request = AccessRequest.objects.create(
            user=user,
            barrier=barrier,
            request_type=AccessRequest.RequestType.FROM_BARRIER,
        )
        assert str(request) == f"`{barrier}` -> `{user}` [{request.status}]"

    def test_delete_raises(self, user, barrier):
        request = AccessRequest.objects.create(
            user=user,
            barrier=barrier,
            request_type=AccessRequest.RequestType.FROM_USER,
        )
        with pytest.raises(PermissionDenied):
            request.delete()

    def test_valid_status_transition_sets_finished_at(self, user, barrier):
        request = AccessRequest.objects.create(
            user=user,
            barrier=barrier,
            request_type=AccessRequest.RequestType.FROM_USER,
        )
        assert request.finished_at is None

        request.status = AccessRequest.Status.ACCEPTED
        request.save()

        assert request.finished_at is not None

    def test_status_does_not_change_finished_at_again(self, user, barrier):
        request = AccessRequest.objects.create(
            user=user,
            barrier=barrier,
            request_type=AccessRequest.RequestType.FROM_USER,
        )
        request.status = AccessRequest.Status.ACCEPTED
        request.save()
        finished_time = request.finished_at

        request.hidden_for_user = True
        request.save()
        assert request.finished_at == finished_time
