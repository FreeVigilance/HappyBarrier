import pytest

from conftest import ADMIN_PHONE, OTHER_PHONE
from verifications.models import Verification


@pytest.fixture
def login_verification(create_verification):
    """Creates a test verification entry with login mode"""

    return create_verification(mode=Verification.Mode.LOGIN, status=Verification.Status.SENT)


@pytest.fixture
def delete_verification(create_verification):
    """Creates a test verification entry with delete mode"""

    return create_verification(mode=Verification.Mode.DELETE_ACCOUNT, status=Verification.Status.VERIFIED)


@pytest.fixture
def verified_verification(create_verification):
    """Creates a verified verification entry"""

    return create_verification(status=Verification.Status.VERIFIED)


@pytest.fixture
def old_phone_verification(create_verification):
    """Creates a verified verification entry for old phone number"""

    return create_verification(mode=Verification.Mode.CHANGE_PHONE_OLD, status=Verification.Status.VERIFIED)


@pytest.fixture
def new_phone_verification(create_verification):
    """Creates a verified verification entry for new phone number"""

    return create_verification(
        phone=OTHER_PHONE, mode=Verification.Mode.CHANGE_PHONE_NEW, status=Verification.Status.VERIFIED
    )


@pytest.fixture
def password_verification(create_verification):
    """Creates a verified verification entry for password"""

    return create_verification(
        phone=ADMIN_PHONE, mode=Verification.Mode.CHANGE_PASSWORD, status=Verification.Status.VERIFIED
    )


@pytest.fixture
def reset_verification(create_verification):
    """Creates a verified verification entry for new phone number"""

    return create_verification(
        phone=ADMIN_PHONE, mode=Verification.Mode.RESET_PASSWORD, status=Verification.Status.VERIFIED
    )
