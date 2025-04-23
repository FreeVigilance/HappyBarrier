import pytest
from django.core.exceptions import ValidationError

from verifications.validators import VerificationCodeValidator, VerificationTokenValidator


@pytest.mark.parametrize(
    "code, is_valid",
    [
        ("123456", True),
        ("000000", True),
        ("12345", False),
        ("1234567", False),
        ("12a456", False),
        ("abcdef", False),
    ],
    ids=[
        "valid_numeric",
        "edge_all_zeros",
        "too_short",
        "too_long",
        "contains_letter",
        "all_letters",
    ],
)
def test_verification_code_validator(code, is_valid):
    validator = VerificationCodeValidator()
    if is_valid:
        assert validator(code) is None
    else:
        with pytest.raises(ValidationError):
            validator(code)


@pytest.mark.parametrize(
    "token, is_valid",
    [
        ("a1b2c3d4e5f6g7h8j9k0l1m2n3p4q5r6", True),
        ("A1B2C3D4E5F6G7H8J9K0L1M2N3P4Q5R6", True),
        ("a1b2c3d4e5f6", False),
        ("a1b2c3d4e5f6g7h8j9k0l1m2n3p4q5r6s77777777777", False),
        ("a1b2c3d4e5f6g7h8j9k0l1m2n3p4q5r$!!", False),
    ],
    ids=[
        "valid_lowercase",
        "valid_uppercase",
        "too_short",
        "too_long",
        "invalid_characters",
    ],
)
def test_verification_token_validator(token, is_valid):
    validator = VerificationTokenValidator()
    if is_valid:
        assert validator(token) is None
    else:
        with pytest.raises(ValidationError):
            validator(token)
