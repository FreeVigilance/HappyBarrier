from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models

from core.constants import CHOICE_MAX_LENGTH, PHONE_MAX_LENGTH, STRING_MAX_LENGTH
from core.validators import PhoneNumberValidator


class Barrier(models.Model):
    """Barrier model representing a physical gate or access point."""

    class Meta:
        db_table = "barrier"

    # TODO - move into config file
    class Model(models.TextChoices):
        RTU5025 = "RTU5025", "RTU5025"
        RTU5035 = "RTU5035", "RTU5035"
        TELEMETRICA = "Telemetrica", "Telemetrica"
        ELFOC = "Elfoc", "Elfoc"

    address = models.CharField(
        max_length=STRING_MAX_LENGTH * 2,
        db_index=True,
        help_text="Full address of the barrier, validated based on frontend suggestions.",
    )

    owner = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,
        related_name="owned_barriers",  # for searching barriers for user - user.managed_barriers.all()
        help_text="User who owns the barrier. Must be an admin.",
    )

    device_phone = models.CharField(
        max_length=PHONE_MAX_LENGTH,
        db_index=True,
        validators=[PhoneNumberValidator()],
        help_text="Enter a phone number in the format +7XXXXXXXXXX.",
    )

    device_model = models.CharField(max_length=CHOICE_MAX_LENGTH, choices=Model.choices)

    device_phones_amount = models.PositiveIntegerField(
        default=1, help_text="Number of registered device phones. Must be at least 1."
    )

    device_password = models.CharField(max_length=20, null=True, blank=True, help_text="Device password for managing.")

    additional_info = models.TextField(blank=True, help_text="Additional details about the barrier.")

    is_public = models.BooleanField(default=True, help_text="Whether the barrier is visible to all users.")

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.address} ({self.owner.full_name})"

    def delete(self, *args, **kwargs):
        raise PermissionDenied("Deletion of this object is not allowed.")


class UserBarrier(models.Model):
    """Link table between users and barriers"""

    class Meta:
        db_table = "user_barrier"
        unique_together = ("user", "barrier")

    user = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,
        related_name="barriers_access",
        help_text="User who has access to the barrier.",
    )

    barrier = models.ForeignKey(
        "barriers.Barrier",
        on_delete=models.PROTECT,
        related_name="users_access",
        help_text="Barrier to which the user has access.",
    )

    access_request = models.ForeignKey(
        "access_requests.AccessRequest",
        on_delete=models.PROTECT,
        help_text="The request from which this access was created.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user} - {self.barrier}"

    @classmethod
    def create(cls, user, barrier, access_request):
        """Create new or reactivate existing inactive user-barrier link"""

        if access_request is None:
            raise ValidationError("Access request is required to create a user-barrier link.")

        if access_request.user != user or access_request.barrier != barrier:
            raise ValidationError("Access request does not match given user and barrier.")

        existing = cls.objects.filter(user=user, barrier=barrier).first()
        if existing:
            if existing.is_active:
                raise ValidationError("An active access already exists for this user and barrier.")
            else:
                existing.is_active = True
                existing.access_request = access_request
                existing.save(update_fields=["is_active", "access_request"])
                return existing

        return cls.objects.create(user=user, barrier=barrier, access_request=access_request)

    @classmethod
    def user_has_access_to_barrier(cls, user, barrier):
        """Returns True if the given user has access to the specified barrier."""

        return cls.objects.filter(user=user, barrier=barrier, is_active=True).exists()

    def delete(self, *args, **kwargs):
        raise PermissionDenied("Deletion of this object is not allowed.")


class BarrierLimit(models.Model):
    """Limits for a barrier."""

    class Meta:
        db_table = "barrier_limit"

    barrier = models.OneToOneField(
        "barriers.Barrier",
        on_delete=models.PROTECT,
        related_name="limits",
        help_text="Barrier associated with the limits.",
    )

    user_phone_limit = models.PositiveIntegerField(
        null=True, blank=True, help_text="Maximum number of phone numbers a user can register"
    )

    user_temp_phone_limit = models.PositiveIntegerField(
        null=True, blank=True, help_text="Maximum number of temporary phone numbers allowed per user"
    )

    global_temp_phone_limit = models.PositiveIntegerField(
        null=True, blank=True, help_text="Maximum number of temporary phone numbers allowed in total"
    )

    user_schedule_phone_limit = models.PositiveIntegerField(
        null=True, blank=True, help_text="Maximum number of schedule phone numbers allowed per user"
    )

    global_schedule_phone_limit = models.PositiveIntegerField(
        null=True, blank=True, help_text="Maximum number of schedule phone numbers allowed in total"
    )

    schedule_interval_limit = models.PositiveIntegerField(
        null=True, blank=True, help_text="Maximum number of schedule phone numbers allowed in total"
    )

    sms_weekly_limit = models.PositiveIntegerField(
        null=True, blank=True, help_text="Maximum number of SMS messages a user can send per week"
    )

    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when limits were created")
    updated_at = models.DateTimeField(auto_now=True, help_text="Timestamp when limits were last updated")

    def __str__(self):
        limits = []

        if self.user_phone_limit is not None:
            limits.append(f"user_phones: {self.user_phone_limit}")
        if self.user_temp_phone_limit is not None:
            limits.append(f"user_temp_phones: {self.user_temp_phone_limit}")
        if self.global_temp_phone_limit is not None:
            limits.append(f"temp_all: {self.global_temp_phone_limit}")
        if self.sms_weekly_limit is not None:
            limits.append(f"sms_in_week: {self.sms_weekly_limit}")

        limits_str = f"[{', '.join(limits)}]" if limits else "[]"

        return f"Limits for Barrier '{self.barrier.address}' (ID: {self.barrier.id}) — {limits_str}"

    def delete(self, *args, **kwargs):
        raise PermissionDenied("Deletion of this object is not allowed.")
