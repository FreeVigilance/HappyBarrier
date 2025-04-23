import pytest

from barriers.models import Barrier
from conftest import BARRIER_DEVICE_PASSWORD

OTHER_BARRIER_ADDRESS = "St. Another, 9"
OTHER_BARRIER_DEVICE_PHONE = "+70000000003"


@pytest.fixture
def other_barrier(another_admin):
    return Barrier.objects.create(
        address=OTHER_BARRIER_ADDRESS,
        owner=another_admin,
        device_phone=OTHER_BARRIER_DEVICE_PHONE,
        device_model=Barrier.Model.ELFOC,
        device_phones_amount=10,
        device_password=BARRIER_DEVICE_PASSWORD,
        additional_info="Testing other barrier",
        is_public=True,
    )


@pytest.fixture
def other_admin_barrier(admin_user):
    return Barrier.objects.create(
        address=OTHER_BARRIER_ADDRESS,
        owner=admin_user,
        device_phone=OTHER_BARRIER_DEVICE_PHONE,
        device_model=Barrier.Model.ELFOC,
        device_phones_amount=10,
        device_password=BARRIER_DEVICE_PASSWORD,
        additional_info="Testing other barrier",
        is_public=True,
    )
