import pytest
from django.core.exceptions import ValidationError

from core.validators import PhoneNumberValidator


@pytest.mark.parametrize(
    "phone, is_valid",
    [
        ("+79991234567", True),  # Valid phone number
        ("79991234567", False),  # Missing "+"
        ("+89991234567", False),  # Wrong country code
        ("+7999123456", False),  # Too short
        ("+799912345678", False),  # Too long
        ("+7abcdefghij", False),  # Contains letters
    ],
)
def test_phone_number_validator(phone, is_valid):
    validator = PhoneNumberValidator()
    if is_valid:
        assert validator(phone) is None  # Should pass validation
    else:
        with pytest.raises(ValidationError):
            validator(phone)  # Should raise ValidationError
