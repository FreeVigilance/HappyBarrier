import pytest
from django.core.exceptions import ValidationError

from barriers.validators import DevicePasswordValidator

validator = DevicePasswordValidator()


@pytest.mark.parametrize("valid_password", ["1234", "0000", "9876"])
def test_valid_passwords(valid_password):
    assert validator(valid_password) is None


@pytest.mark.parametrize("invalid_password", ["", "123", "12345", "abcd", "12a4", "    ", "12 3", "12-3"])
def test_invalid_passwords(invalid_password):
    with pytest.raises(ValidationError):
        validator(invalid_password)
