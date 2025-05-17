from django.core.exceptions import PermissionDenied
from django.db import models
from django.utils.timezone import now

from barriers.models import Barrier
from core.constants import CHOICE_MAX_LENGTH


class BarrierActionLog(models.Model):
    """Tracks actions performed on phones/barriers by users or admins."""

    class Meta:
        db_table = "barrier_action_log"
        indexes = [models.Index(fields=["created_at", "phone", "barrier"])]

    class Author(models.TextChoices):
        USER = "user", "User"
        ADMIN = "admin", "Admin"
        SYSTEM = "system", "System"

    class ActionType(models.TextChoices):
        ADD_PHONE = "add_phone", "Add Phone"
        DELETE_PHONE = "delete_phone", "Delete Phone"
        UPDATE_PHONE = "update_phone", "Update Phone"
        BARRIER_SETTING = "barrier_setting", "Barrier Setting"

    class Reason(models.TextChoices):
        MANUAL = "manual", "Manual Action"
        ACCESS_GRANTED = "access_granted", "Access Granted"
        PRIMARY_PHONE_CHANGE = "primary_phone_change", "Primary Phone Changed"
        SCHEDULE_UPDATE = "schedule_update", "Schedule Updated"
        END_OF_TIME = "end_time", "Deleting phone after its time ended"
        BARRIER_EXIT = "barrier_exit", "User Left Barrier or Admin deleted user from barrier"
        BARRIER_DELETED = "barrier_deleted", "Barrier Deleted"
        USER_DELETED = "user_deleted", "User Deleted"

    phone = models.ForeignKey(
        "phones.BarrierPhone",
        on_delete=models.PROTECT,
        related_name="action_histories",
        null=True,
        blank=True,
        help_text="Phone involved in the action, if any",
    )

    barrier = models.ForeignKey(
        Barrier,
        on_delete=models.PROTECT,
        related_name="action_histories",
        help_text="Barrier associated with the action",
    )

    author = models.CharField(max_length=CHOICE_MAX_LENGTH, choices=Author.choices)
    action_type = models.CharField(max_length=CHOICE_MAX_LENGTH, choices=ActionType.choices)
    reason = models.CharField(max_length=CHOICE_MAX_LENGTH, choices=Reason.choices)

    old_value = models.TextField(null=True, blank=True, help_text="String representation of the previous value/state.")
    new_value = models.TextField(null=True, blank=True, help_text="String representation of the new value/state.")

    created_at = models.DateTimeField(default=now)

    def __str__(self):
        return (
            f"'{self.id}' [{self.created_at:%Y-%m-%d %H:%M}] by {self.author} {self.action_type} ({self.reason}) "
            f"for {self.phone}"
        )

    def delete(self, *args, **kwargs):
        raise PermissionDenied("Action history records cannot be deleted.")
