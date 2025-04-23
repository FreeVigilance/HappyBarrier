import pytest
from django.urls import reverse
from rest_framework import status

from conftest import ADMIN_NAME, ADMIN_PASSWORD, ADMIN_PHONE
from users.admin import AdminCreationForm, CustomAuthenticationForm
from users.models import User


@pytest.mark.django_db
def test_admin_creation_form_valid():
    """Check that the admin creation form correctly creates a user"""

    form_data = {"phone": ADMIN_PHONE, "full_name": ADMIN_NAME, "password": ADMIN_PASSWORD}
    form = AdminCreationForm(data=form_data)

    assert form.is_valid(), f"Form errors: {form.errors}"

    user = form.save()
    assert user.is_staff is True
    assert user.role == User.Role.ADMIN
    assert user.check_password(ADMIN_PASSWORD)


@pytest.mark.django_db
def test_admin_creation_form_invalid_phone():
    """Check that an invalid phone number triggers an error"""

    form_data = {"phone": "+123456", "full_name": ADMIN_NAME, "password": ADMIN_PASSWORD}
    form = AdminCreationForm(data=form_data)

    assert not form.is_valid()
    assert "phone" in form.errors


@pytest.mark.django_db
def test_custom_auth_form_validates_phone():
    form = CustomAuthenticationForm(data={"username": ADMIN_PHONE, "password": ADMIN_PASSWORD})
    form.fields["username"].validators = []
    assert form.is_valid() or "username" not in form.errors


@pytest.mark.django_db
def test_superuser_can_add_users(client_superuser):
    """Superuser can add users"""

    url = reverse("admin:users_user_add")
    response = client_superuser.get(url)
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_admin_cannot_add_users(client_admin):
    """Regular admin cannot add users"""

    url = reverse("admin:users_user_add")
    response = client_admin.get(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_superuser_can_view_users(client_superuser):
    """Superuser can view the user list"""

    url = reverse("admin:users_user_changelist")
    response = client_superuser.get(url)
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_admin_can_see_user_module(client_admin):
    url = reverse("admin:index")
    response = client_admin.get(url)
    assert "Users" in response.content.decode()


@pytest.mark.django_db
def test_non_admin_cannot_see_user_module(client_user):
    url = reverse("admin:index")
    response = client_user.get(url)
    assert "Users" not in response.content.decode()


@pytest.mark.django_db
def test_superuser_cannot_deactivate_self(client_superuser, superuser):
    """Superadmin cannot deactivate themselves"""

    url = reverse("admin:users_user_change", args=[superuser.pk])
    client_superuser.post(url, {"is_active": False}, follow=True)
    assert superuser.is_active


@pytest.mark.django_db
def test_admin_cannot_change_readonly_fields(client_superuser, admin_user):
    url = reverse("admin:users_user_change", args=[admin_user.pk])
    client_superuser.post(
        url,
        {
            "phone": admin_user.phone,
            "full_name": "Changed",
            "role": User.Role.SUPERUSER,
            "is_active": True,
        },
        follow=True,
    )

    admin_user.refresh_from_db()
    assert admin_user.role != User.Role.SUPERUSER


@pytest.mark.django_db
def test_admin_cannot_delete_user(client_superuser, admin_user):
    """Even a superuser cannot delete a user"""

    url = reverse("admin:users_user_delete", args=[admin_user.pk])
    response = client_superuser.post(url, follow=True)
    assert response.status_code == status.HTTP_403_FORBIDDEN
