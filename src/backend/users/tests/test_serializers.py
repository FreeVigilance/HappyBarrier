import pytest

from conftest import ADMIN_PASSWORD, ADMIN_PHONE, USER_NAME, USER_PHONE
from users.models import User
from users.serializers import (
    AdminPasswordVerificationSerializer,
    ChangePasswordSerializer,
    ChangePhoneSerializer,
    CheckAdminSerializer,
    DeleteUserSerializer,
    LoginSerializer,
    ResetPasswordSerializer,
    SearchUserSerializer,
    UpdateUserSerializer,
    UserSerializer,
)

INVALID_TOKEN = "a1b2c3"
VALID_TOKEN = "a1b2c3d4e5f6g7h8j9k0l1m2n3p4q5r6"
INVALID_PHONE = "89991234567"


@pytest.mark.parametrize(
    "data, is_valid",
    [
        ({"phone": ADMIN_PHONE, "password": ADMIN_PASSWORD}, True),
        ({"phone": INVALID_PHONE, "password": ADMIN_PASSWORD}, False),
        ({"phone": ADMIN_PHONE}, False),
    ],
    ids=[
        "valid data",
        "invalid phone format",
        "missing password",
    ],
)
def test_admin_password_verification_serializer(data, is_valid):
    serializer = AdminPasswordVerificationSerializer(data=data)
    assert serializer.is_valid() == is_valid


@pytest.mark.parametrize(
    "data, is_valid",
    [
        ({"phone": USER_PHONE, "verification_token": VALID_TOKEN}, True),
        ({"phone": INVALID_PHONE, "verification_token": VALID_TOKEN}, False),
        ({"phone": ADMIN_PHONE, "verification_token": INVALID_TOKEN}, False),
        ({"phone": USER_PHONE}, False),
    ],
    ids=[
        "valid data",
        "invalid phone format",
        "invalid verification token format",
        "missing verification token",
    ],
)
def test_login_serializer(data, is_valid):
    serializer = LoginSerializer(data=data)
    assert serializer.is_valid() == is_valid


@pytest.mark.parametrize(
    "data, is_valid",
    [
        ({"phone": ADMIN_PHONE}, True),
        ({"phone": INVALID_PHONE}, False),
        ({}, False),
    ],
    ids=[
        "valid data",
        "invalid phone format",
        "missing phone",
    ],
)
def test_check_admin_serializer(data, is_valid):
    serializer = CheckAdminSerializer(data=data)
    assert serializer.is_valid() == is_valid


@pytest.mark.django_db
def test_user_serializer_output_fields(user):
    serializer = UserSerializer(user)
    data = serializer.data

    expected_fields = {"id", "phone", "full_name", "role", "phone_privacy", "is_active"}
    assert set(data.keys()) == expected_fields

    assert data["id"] == user.id
    assert data["phone"] == user.phone
    assert data["full_name"] == user.full_name
    assert data["role"] == user.role
    assert data["phone_privacy"] == user.phone_privacy
    assert data["is_active"] == user.is_active


@pytest.mark.parametrize(
    "data, is_valid",
    [
        ({"full_name": USER_NAME, "phone_privacy": User.PhonePrivacy.PRIVATE}, True),
        ({"full_name": "", "phone_privacy": User.PhonePrivacy.PUBLIC}, True),
        ({"phone_privacy": User.PhonePrivacy.PROTECTED}, True),
        ({"full_name": USER_NAME, "phone_privacy": "invalid"}, False),
        ({}, True),
    ],
    ids=[
        "valid data",
        "valid data with empty name",
        "valid data without name",
        "invalid privacy type",
        "empty data",
    ],
)
def test_update_user_serializer(data, is_valid):
    serializer = UpdateUserSerializer(data=data)
    assert serializer.is_valid() == is_valid


@pytest.mark.parametrize(
    "data, is_valid",
    [
        ({"verification_token": VALID_TOKEN}, True),
        ({"verification_token": INVALID_TOKEN}, False),
        ({}, False),
    ],
    ids=[
        "valid data",
        "invalid token format",
        "missing token",
    ],
)
def test_delete_user_serializer(data, is_valid):
    serializer = DeleteUserSerializer(data=data)
    assert serializer.is_valid() == is_valid


@pytest.mark.django_db
@pytest.mark.parametrize(
    "data, is_valid",
    [
        ({"new_phone": USER_PHONE, "old_verification_token": VALID_TOKEN, "new_verification_token": VALID_TOKEN}, True),
        ({"new_phone": USER_PHONE, "old_verification_token": VALID_TOKEN}, False),
        (
            {
                "new_phone": INVALID_PHONE,
                "old_verification_token": VALID_TOKEN,
                "new_verification_token": VALID_TOKEN,
            },
            False,
        ),
        (
            {
                "new_phone": USER_PHONE,
                "old_verification_token": INVALID_PHONE,
                "new_verification_token": VALID_TOKEN,
            },
            False,
        ),
    ],
    ids=[
        "valid data",
        "invalid token format",
        "invalid phone format",
        "missing token",
    ],
)
def test_change_phone_serializer(data, is_valid):
    serializer = ChangePhoneSerializer(data=data)
    assert serializer.is_valid() == is_valid


@pytest.mark.parametrize(
    "data, is_valid",
    [
        ({"old_password": "OldPass123!", "new_password": "NewPass456!", "verification_token": VALID_TOKEN}, True),
        ({"old_password": "", "new_password": "NewPass456!", "verification_token": VALID_TOKEN}, False),
        ({"old_password": "OldPass123!", "new_password": "short", "verification_token": VALID_TOKEN}, False),
    ],
    ids=[
        "valid data",
        "empty old password",
        "short new password",
    ],
)
def test_change_password_serializer(data, is_valid, mocker):
    request_mock = mocker.Mock()
    request_mock.user.check_password.return_value = data.get("old_password") == "OldPass123!"

    serializer = ChangePasswordSerializer(data=data, context={"request": request_mock})
    assert serializer.is_valid() == is_valid


@pytest.mark.django_db
def test_change_phone_with_existing_number(user):
    data = {
        "new_phone": user.phone,  # already used phone
        "old_verification_token": VALID_TOKEN,
        "new_verification_token": VALID_TOKEN,
    }
    serializer = ChangePhoneSerializer(data=data)

    assert not serializer.is_valid()
    assert "Given new phone number is already in use." in serializer.errors["new_phone"]


def test_incorrect_old_password_raises_error(mocker):
    data = {"old_password": "WrongOldPass", "new_password": "NewPass456!", "verification_token": VALID_TOKEN}
    request_mock = mocker.Mock()
    request_mock.user.check_password.return_value = False

    serializer = ChangePasswordSerializer(data=data, context={"request": request_mock})
    assert not serializer.is_valid()

    assert "Current password is incorrect." in serializer.errors["old_password"]


@pytest.mark.parametrize(
    "data, is_valid",
    [
        ({"phone": ADMIN_PHONE, "new_password": "NewSecurePass!", "verification_token": VALID_TOKEN}, True),
        ({"phone": INVALID_PHONE, "new_password": "NewSecurePass!", "verification_token": VALID_TOKEN}, False),
        ({"phone": ADMIN_PHONE, "new_password": "short", "verification_token": VALID_TOKEN}, False),
    ],
    ids=[
        "valid data",
        "invalid phone format",
        "short new password",
    ],
)
def test_reset_password_serializer(data, is_valid):
    serializer = ResetPasswordSerializer(data=data)
    assert serializer.is_valid() == is_valid


@pytest.mark.parametrize(
    "data, is_valid",
    [
        ({"phone": ADMIN_PHONE}, True),
        ({"phone": INVALID_PHONE}, False),
        ({}, False),
    ],
    ids=[
        "valid data",
        "invalid phone format",
        "missing phone",
    ],
)
def test_search_user_serializer(data, is_valid):
    serializer = SearchUserSerializer(data=data)
    assert serializer.is_valid() == is_valid
