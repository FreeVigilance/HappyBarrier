import pytest
from django.utils.timezone import now
from rest_framework.test import APIClient

from access_requests.models import AccessRequest
from barriers.models import Barrier, UserBarrier
from users.models import User
from verifications.models import Verification, VerificationService

USER_PHONE = "+79991234567"
ADMIN_PHONE = "+79995554433"
ANOTHER_ADMIN_PHONE = "+79992223311"
SUPERUSER_PHONE = "+79994443322"
OTHER_PHONE = "+79999999999"
BARRIER_DEVICE_PHONE = "+70000000001"
PRIVATE_BARRIER_DEVICE_PHONE = "+70000000002"
BLOCKED_USER_PHONE = "+79993332211"
ADMIN_PASSWORD = "adminpassword"
ANOTHER_ADMIN_PASSWORD = "anotheradminpass"
SUPERUSER_PASSWORD = "SuperSecurePass"
USER_NAME = "John User"
ADMIN_NAME = "Admin"
BARRIER_ADDRESS = "Street Barrier"
PRIVATE_BARRIER_ADDRESS = "Private Barrier"
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
    return User.objects.create_admin(phone=OTHER_PHONE, full_name=USER_NAME)


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
def barrier(admin_user):
    """A public barrier owned by admin"""

    return Barrier.objects.create(
        address=BARRIER_ADDRESS,
        owner=admin_user,
        device_phone=BARRIER_DEVICE_PHONE,
        device_model=Barrier.Model.RTU5025,
        device_phones_amount=10,
        is_public=True,
    )


@pytest.fixture
def private_barrier(admin_user):
    """A private barrier not accessible to regular user"""

    return Barrier.objects.create(
        address=PRIVATE_BARRIER_ADDRESS,
        owner=admin_user,
        device_phone=PRIVATE_BARRIER_DEVICE_PHONE,
        device_model=Barrier.Model.RTU5035,
        device_password="1234",
        device_phones_amount=10,
        is_public=False,
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
