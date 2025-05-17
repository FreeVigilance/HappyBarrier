from datetime import time, timedelta

import pytest
from django.utils.timezone import now
from rest_framework.test import APIClient

from access_requests.models import AccessRequest
from action_history.models import BarrierActionLog
from barriers.models import Barrier, UserBarrier
from phones.constants import MINIMUM_TIME_INTERVAL_MINUTES
from phones.models import BarrierPhone
from users.models import User
from verifications.models import Verification, VerificationService

USER_PHONE = "+79991234567"
ADMIN_PHONE = "+79995554433"
ANOTHER_ADMIN_PHONE = "+79992223311"
SUPERUSER_PHONE = "+79994443322"
OTHER_PHONE = "+79999999999"
BARRIER_DEVICE_PHONE = "+70000000001"
PRIVATE_BARRIER_DEVICE_PHONE = "+70000000002"
OTHER_BARRIER_DEVICE_PHONE = "+70000000006"
BLOCKED_USER_PHONE = "+79993332211"
BARRIER_PERMANENT_PHONE = "+70000000003"
BARRIER_PERMANENT_PHONE_NAME = "Permanent Phone"
BARRIER_TEMPORARY_PHONE = "+70000000004"
BARRIER_SCHEDULE_PHONE = "+70000000005"
ADMIN_PASSWORD = "adminpassword"
ANOTHER_ADMIN_PASSWORD = "anotheradminpass"
SUPERUSER_PASSWORD = "SuperSecurePass"
USER_NAME = "John User"
ADMIN_NAME = "Admin"
BARRIER_ADDRESS = "Street Barrier"
PRIVATE_BARRIER_ADDRESS = "Private Barrier"
OTHER_BARRIER_ADDRESS = "St. Another, 9"
BARRIER_DEVICE_PASSWORD = "1234"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def authenticated_admin_client(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def user():
    return User.objects.create_user(phone=USER_PHONE, full_name=USER_NAME)


@pytest.fixture
def another_user():
    return User.objects.create_user(phone=OTHER_PHONE, full_name=USER_NAME)


@pytest.fixture
def admin_user():
    return User.objects.create_admin(phone=ADMIN_PHONE, password=ADMIN_PASSWORD)


@pytest.fixture
def another_admin():
    return User.objects.create_admin(phone=ANOTHER_ADMIN_PHONE, password=ANOTHER_ADMIN_PASSWORD)


@pytest.fixture
def superuser():
    return User.objects.create_superuser(phone=SUPERUSER_PHONE, password=SUPERUSER_PASSWORD)


@pytest.fixture
def blocked_user():
    return User.objects.create_user(phone=BLOCKED_USER_PHONE, is_active=False, block_reason="Spamming")


@pytest.fixture
def client_user(user, client):
    client.force_login(user)
    return client


@pytest.fixture
def client_superuser(superuser, client):
    client.force_login(superuser)
    return client


@pytest.fixture
def client_admin(admin_user, client):
    client.force_login(admin_user)
    return client


@pytest.fixture
def create_verification():
    """Factory fixture to create a verification entry"""

    def _create_verification(
        phone=USER_PHONE,
        status=Verification.Status.SENT,
        mode=Verification.Mode.LOGIN,
        code=None,
        verification_token=None,
        created_at=None,
    ):
        return Verification.objects.create(
            phone=phone,
            code=code or VerificationService.generate_verification_code(),
            verification_token=verification_token or VerificationService.generate_verification_token(),
            mode=mode,
            status=status,
            created_at=created_at or now(),
        )

    return _create_verification


@pytest.fixture
def create_barrier():
    """Factory fixture to create a barrier entry"""

    def _create_barrier(
        owner,
        address=BARRIER_ADDRESS,
        device_phone=BARRIER_DEVICE_PHONE,
        device_model=Barrier.Model.RTU5025,
        device_password=BARRIER_DEVICE_PASSWORD,
        device_phones_amount=10,
        is_public=True,
    ):
        return Barrier.objects.create(
            address=address,
            owner=owner,
            device_phone=device_phone,
            device_model=device_model,
            device_password=device_password,
            device_phones_amount=device_phones_amount,
            is_public=is_public,
        )

    return _create_barrier


@pytest.fixture
def barrier(admin_user, create_barrier):
    """A public barrier owned by admin"""

    return create_barrier(owner=admin_user)


@pytest.fixture
def private_barrier(admin_user, create_barrier):
    """A private barrier not accessible to regular user"""

    return create_barrier(
        owner=admin_user, address=PRIVATE_BARRIER_ADDRESS, device_phone=PRIVATE_BARRIER_DEVICE_PHONE, is_public=False
    )


@pytest.fixture
def other_barrier(another_admin, create_barrier):

    return create_barrier(
        address=OTHER_BARRIER_ADDRESS,
        owner=another_admin,
        device_phone=OTHER_BARRIER_DEVICE_PHONE,
        device_model=Barrier.Model.ELFOC,
    )


@pytest.fixture
def other_admin_barrier(admin_user, create_barrier):

    return create_barrier(
        owner=admin_user,
        address=OTHER_BARRIER_ADDRESS,
        device_phone=OTHER_BARRIER_DEVICE_PHONE,
        device_model=Barrier.Model.ELFOC,
    )


@pytest.fixture
def create_access_request():
    """Factory fixture to create an access request entry"""

    def _create_access_request(
        user,
        barrier,
        request_type=AccessRequest.RequestType.FROM_USER,
        status=AccessRequest.Status.PENDING,
    ):
        return AccessRequest.objects.create(
            user=user,
            barrier=barrier,
            request_type=request_type,
            status=status,
        )

    return _create_access_request


@pytest.fixture
def access_request(user, barrier, create_access_request):
    """Access request from user to barrier which was accepted"""

    return create_access_request(user, barrier, status=AccessRequest.Status.ACCEPTED)


@pytest.fixture
def private_barrier_with_access(user, private_barrier, access_request):
    """Private barrier to which the user has access"""

    UserBarrier.objects.create(user=user, barrier=private_barrier, access_request=access_request)
    return private_barrier


@pytest.fixture
def create_barrier_phone():
    """Factory fixture to create a barrier phone entry"""

    def _create_barrier_phone(
        user,
        barrier,
        phone=BARRIER_PERMANENT_PHONE,
        type=BarrierPhone.PhoneType.PERMANENT,
        name=BARRIER_PERMANENT_PHONE_NAME,
        author=BarrierActionLog.Author.SYSTEM,
        reason=BarrierActionLog.Reason.MANUAL,
        start_time=None,
        end_time=None,
        schedule=None,
    ):
        return BarrierPhone.create(
            user=user,
            barrier=barrier,
            phone=phone,
            type=type,
            name=name,
            author=author,
            reason=reason,
            start_time=start_time,
            end_time=end_time,
            schedule=schedule,
        )

    return _create_barrier_phone


@pytest.fixture
def barrier_phone(user, barrier, create_barrier_phone):
    return create_barrier_phone(user, barrier)


@pytest.fixture
def temporary_barrier_phone(user, barrier, create_barrier_phone):
    return create_barrier_phone(
        user,
        barrier,
        phone=BARRIER_TEMPORARY_PHONE,
        type=BarrierPhone.PhoneType.TEMPORARY,
        start_time=now() + timedelta(minutes=MINIMUM_TIME_INTERVAL_MINUTES + 5),
        end_time=now() + timedelta(hours=2),
    )


@pytest.fixture
def schedule_barrier_phone(user, barrier, create_barrier_phone):
    schedule = {
        "monday": [{"start_time": time(9, 0), "end_time": time(10, 0)}],
        "wednesday": [{"start_time": time(14, 0), "end_time": time(15, 0)}],
    }

    return create_barrier_phone(
        user=user,
        barrier=barrier,
        phone=BARRIER_SCHEDULE_PHONE,
        type=BarrierPhone.PhoneType.SCHEDULE,
        name="Schedule Phone",
        schedule=schedule,
    )
