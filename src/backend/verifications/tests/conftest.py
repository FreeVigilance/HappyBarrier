import pytest

from verifications.models import Verification


@pytest.fixture
def verification(create_verification):
    return create_verification()


@pytest.fixture
def verified_verification(create_verification):
    return create_verification(status=Verification.Status.VERIFIED)


@pytest.fixture
def expired_verification(create_verification):
    return create_verification(status=Verification.Status.EXPIRED)
