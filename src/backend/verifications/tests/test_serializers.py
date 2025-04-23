import pytest

from verifications.models import Verification
from verifications.serializers import SendVerificationCodeSerializer, VerifyCodeSerializer

VALID_TOKEN = "a1b2c3d4e5f6g7h8j9k0l1m2n3p4q5r6"


@pytest.mark.parametrize(
    "data, is_valid",
    [
        ({"phone": "+79991234567", "mode": Verification.Mode.LOGIN}, True),
        ({"phone": "89991234567", "mode": Verification.Mode.LOGIN}, False),
        ({"phone": "+79991234567"}, False),
        ({"phone": "", "mode": Verification.Mode.LOGIN}, False),
        ({"phone": None, "mode": Verification.Mode.LOGIN}, False),
        ({"phone": "+79991234567", "mode": "unknown_mode"}, False),
    ],
    ids=[
        "valid data",
        "invalid phone format",
        "missing mode",
        "empty phone",
        "none phone",
        "invalid mode value",
    ],
)
def test_send_verification_code_serializer(data, is_valid):
    serializer = SendVerificationCodeSerializer(data=data)
    assert serializer.is_valid() == is_valid


@pytest.mark.parametrize(
    "data, is_valid",
    [
        ({"phone": "+79991234567", "code": "123456", "verification_token": VALID_TOKEN}, True),
        ({"phone": "+79991234567", "code": "abcdef", "verification_token": VALID_TOKEN}, False),
        ({"phone": "+79991234567", "code": "123456"}, False),
        ({"phone": "+79991234567", "code": "", "verification_token": "a1b2c3"}, False),
        ({"phone": "+79991234567", "code": "123456", "verification_token": ""}, False),
    ],
    ids=[
        "valid data",
        "non-digit code",
        "missing token",
        "empty code",
        "empty token",
    ],
)
def test_verify_code_serializer(data, is_valid):
    serializer = VerifyCodeSerializer(data=data)
    assert serializer.is_valid() == is_valid
