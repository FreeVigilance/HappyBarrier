from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models
from django.utils.timezone import now
from rest_framework import status

from core.constants import CHOICE_MAX_LENGTH, PHONE_MAX_LENGTH, STRING_MAX_LENGTH
from core.utils import error_response
from core.validators import PhoneNumberValidator


class UserManager(BaseUserManager):
    """Custom manager for the User model"""

    phone_validator = PhoneNumberValidator()

    def validate_phone(self, phone: str):
        """Validate phone number using PhoneNumberValidator"""

        try:
            self.phone_validator(phone)
        except ValidationError as e:
            raise ValidationError("Invalid phone number: " + str(e))
        return phone

    def create_user(self, phone, password=None, **extra_fields):
        """Creates a regular user"""

        if not phone:
            raise ValueError("Phone number must be provided")

        phone = self.validate_phone(phone)

        extra_fields.setdefault("role", User.Role.USER)
        extra_fields.setdefault("is_active", True)

        if extra_fields["role"] == User.Role.USER:
            password = None

        user = self.model(phone=phone, **extra_fields)
        if password:
            user.set_password(password)  # Only admins have a password
        user.save(using=self._db)
        return user

    def create_admin(self, phone, password=None, **extra_fields):
        """Creates an admin (can only be created via Django Admin)"""

        extra_fields.setdefault("role", User.Role.ADMIN)
        extra_fields.setdefault("is_staff", True)

        if password is None:
            raise ValueError("Admin users require a password")

        return self.create_user(phone, password, **extra_fields)

    def create_superuser(self, phone, password=None, **extra_fields):
        """Creates a superuser"""

        if self.model.objects.filter(role=User.Role.SUPERUSER).exists():
            raise ValueError("There can be only one superuser")

        extra_fields.setdefault("role", User.Role.SUPERUSER)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_staff", True)

        if password is None:
            raise ValueError("Superuser requires a password")

        return self.create_user(phone, password, **extra_fields)

    def get_by_phone(self, phone: str):
        """Return a user by phone number or None"""

        return self.filter(phone=phone).first()

    def check_phone_blocked(self, phone: str):
        """Returns an error response if the user with this phone is blocked."""

        user = self.get_by_phone(phone)
        if user and not user.is_active:
            reason = user.block_reason
            return error_response(f"User is blocked. Reason: '{reason}'.", status.HTTP_403_FORBIDDEN)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model"""

    class Meta:
        db_table = "user"

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        USER = "user", "User"
        SUPERUSER = "superuser", "Superuser"

    class PhonePrivacy(models.TextChoices):
        PUBLIC = "public", "Public"
        PRIVATE = "private", "Private"
        PROTECTED = "protected", "Protected"

    phone = models.CharField(
        max_length=PHONE_MAX_LENGTH,
        unique=True,
        help_text="Enter a phone number in the format +7XXXXXXXXXX.",
        validators=[PhoneNumberValidator()],
        error_messages={"unique": "A user with this phone number already exists."},
    )
    full_name = models.CharField(max_length=STRING_MAX_LENGTH, blank=True, default="")
    password = models.CharField(max_length=STRING_MAX_LENGTH, blank=True, default="")

    role = models.CharField(max_length=CHOICE_MAX_LENGTH, choices=Role.choices, default=Role.USER)

    phone_privacy = models.CharField(
        max_length=CHOICE_MAX_LENGTH, choices=PhonePrivacy.choices, default=PhonePrivacy.PRIVATE
    )

    is_staff = models.BooleanField(
        default=False,
        help_text="Designates whether the user can log into this admin site.",
    )
    is_superuser = models.BooleanField(
        default=False, help_text="Designates whether the user can manage all aspects of the system."
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Designates whether this user should be treated as active. "
        "Unselect this instead of deleting accounts.",
    )
    is_blocked = models.BooleanField(
        default=True,
        help_text="Designates whether this user should be treated as blocked.",
    )
    block_reason = models.CharField(max_length=STRING_MAX_LENGTH, blank=True, default="")
    date_joined = models.DateTimeField(default=now)
    last_login = models.DateTimeField(blank=True, null=True)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["full_name", "role"]

    def __str__(self):
        return self.phone + " " + self.full_name

    def get_short_name(self):
        return self.phone

    def get_full_name(self):
        return self.full_name

    def get_phone(self):
        return self.phone

    def delete(self, *args, **kwargs):
        raise PermissionDenied("Deletion of this object is not allowed.")
