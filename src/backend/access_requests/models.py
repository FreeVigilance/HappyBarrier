from django.core.exceptions import PermissionDenied
from django.db import models
from django.utils.timezone import now

from core.constants import CHOICE_MAX_LENGTH


class AccessRequest(models.Model):
    """
    Access request between a user and a barrier.

    Tracks who requested access, from whom, and the current status.
    Only allows transitions from 'pending' to 'approved', 'rejected' or 'cancelled'.
    """

    class Meta:
        db_table = "access_request"

    class RequestType(models.TextChoices):
        FROM_USER = "from_user", "From user"
        FROM_BARRIER = "from_barrier", "From barrier"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    ALLOWED_STATUS_TRANSITIONS = {
        Status.PENDING: {Status.ACCEPTED, Status.REJECTED, Status.CANCELLED},
        Status.ACCEPTED: set(),
        Status.REJECTED: set(),
        Status.CANCELLED: set(),
    }

    user = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,
        related_name="access_requests",
        help_text="User who requests access.",
    )

    barrier = models.ForeignKey(
        "barriers.Barrier",
        on_delete=models.PROTECT,
        related_name="access_requests",
        help_text="Barrier to which access is requested.",
    )

    request_type = models.CharField(
        max_length=CHOICE_MAX_LENGTH,
        choices=RequestType.choices,
        help_text="Direction of the access request",
    )

    status = models.CharField(
        max_length=CHOICE_MAX_LENGTH,
        choices=Status.choices,
        default=Status.PENDING,
        help_text="Current status of the access request",
    )

    hidden_for_user = models.BooleanField(default=False)
    hidden_for_admin = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        if self.request_type == AccessRequest.RequestType.FROM_USER:
            return f"`{self.user}` -> `{self.barrier}` [{self.status}]"
        else:
            return f"`{self.barrier}` -> `{self.user}` [{self.status}]"

    def save(self, *args, **kwargs):
        if self.status != self.Status.PENDING and not self.finished_at:
            self.finished_at = now()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionDenied("Deletion of this object is not allowed.")
