from datetime import time
from enum import Enum

from django.core.exceptions import ValidationError

from phones.models import BarrierPhone, ScheduleTimeInterval


class JobAction(str, Enum):
    OPEN = "open"
    CLOSE = "close"
    DELETE = "delete"


def generate_job_id(
    action: JobAction,
    phone_id: int,
    phone_type: BarrierPhone.PhoneType,
    day: ScheduleTimeInterval.DayOfWeek = None,
    time_: time = None,
) -> str:
    """Generate a unique job ID for APScheduler jobs."""

    if phone_type == BarrierPhone.PhoneType.SCHEDULE:
        if not day or not time_:
            raise ValidationError("Day and time are required for schedule-based jobs.")
        if action == JobAction.DELETE:
            raise ValidationError("Cannot delete schedule-based jobs.")
        return f"{phone_type.value}_{action.value}_{phone_id}_{day}_{time_.hour:02d}{time_.minute:02d}"

    if phone_type == BarrierPhone.PhoneType.TEMPORARY:
        return f"{phone_type.value}_{action.value}_{phone_id}"

    raise ValidationError("Phone type must be SCHEDULE or TEMPORARY.")


def parse_job_id(job_id: str):
    """Parses a job ID string into its components. Returns a dict."""

    parts = job_id.split("_")

    if len(parts) == 3 and parts[0] == BarrierPhone.PhoneType.TEMPORARY:
        return {
            "phone_type": BarrierPhone.PhoneType(parts[0]),
            "action": JobAction(parts[1]),
            "phone_id": int(parts[2]),
            "day": None,
            "time": None,
        }

    elif len(parts) == 5 and parts[0] == BarrierPhone.PhoneType.SCHEDULE:
        return {
            "phone_type": BarrierPhone.PhoneType(parts[0]),
            "action": JobAction(parts[1]),
            "phone_id": int(parts[2]),
            "day": parts[3],
            "time": time(hour=int(parts[4][:2]), minute=int(parts[4][2:])),
        }

    raise ValidationError(f"Invalid job ID format: {job_id}")
