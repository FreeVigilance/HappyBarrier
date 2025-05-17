import logging
from datetime import timedelta

from django.utils.timezone import now
from rest_framework.exceptions import ValidationError

from barriers.models import BarrierLimit
from core.utils import ConflictError
from phones.constants import MINIMUM_TIME_INTERVAL_MINUTES

logger = logging.getLogger(__name__)


def validate_temporary_phone(phone_type, start_time, end_time):
    from phones.models import BarrierPhone

    def validate_temporary_phone_dates(start_time, end_time):
        if not start_time or not end_time:
            raise ValidationError({"time": "start_time and end_time are required for temporary phone."})
        if start_time < now() + timedelta(minutes=MINIMUM_TIME_INTERVAL_MINUTES):
            message = f"start_time must be at least {MINIMUM_TIME_INTERVAL_MINUTES} minutes in the future."
            raise ValidationError({"start_time": message})
        if end_time <= start_time:
            raise ValidationError({"end_time": "end_time must be after start_time."})
        if end_time - start_time < timedelta(minutes=MINIMUM_TIME_INTERVAL_MINUTES):
            raise ValidationError({"time": f"Interval must be at least {MINIMUM_TIME_INTERVAL_MINUTES} minutes long."})

    if phone_type == BarrierPhone.PhoneType.TEMPORARY:
        validate_temporary_phone_dates(start_time, end_time)
    elif start_time or end_time:
        message = "start_time and end_time are only allowed for temporary phone numbers."
        raise ValidationError({"time": message})


def validate_schedule_phone(phone_type, schedule, barrier):
    from phones.models import BarrierPhone

    if phone_type == BarrierPhone.PhoneType.SCHEDULE:
        if not schedule:
            raise ValidationError({"schedule": "Schedule is required for schedule phone type."})

        total_intervals = sum(len(intervals) for intervals in schedule.values())
        if total_intervals == 0:
            raise ValidationError({"schedule": "Schedule must contain at least one interval."})

        limits = BarrierLimit.objects.filter(barrier=barrier).first()
        if limits and limits.schedule_interval_limit is not None and total_intervals > limits.schedule_interval_limit:
            message = f"Phone schedule exceeds allowed number of intervals ({limits.schedule_interval_limit} max)."
            raise ConflictError(message)

    elif schedule:
        raise ValidationError({"schedule": "Schedule is only allowed for schedule phone type."})


def validate_limits(phone_type, barrier, user):
    """Check barrier phone limits."""

    from phones.models import BarrierPhone

    def validate_limit(limit, current_count, error_message):
        if limit is not None and current_count >= limit:
            logger.warning(f"Limit exceeded: {error_message}")
            raise ConflictError(error_message)

    limits = BarrierLimit.objects.filter(barrier=barrier).first()
    if not limits:
        return

    existing_phones = BarrierPhone.objects.filter(barrier=barrier, is_active=True)

    validate_limit(
        limits.user_phone_limit,
        existing_phones.filter(user=user).count(),
        f"User has reached the limit of {limits.user_phone_limit} phone numbers.",
    )

    if phone_type == BarrierPhone.PhoneType.TEMPORARY:
        user_temp_count = existing_phones.filter(user=user, type=phone_type).count()
        global_temp_count = existing_phones.filter(type=phone_type).count()

        validate_limit(
            limits.user_temp_phone_limit,
            user_temp_count,
            f"User has reached the limit of {limits.user_temp_phone_limit} temporary phone numbers.",
        )
        validate_limit(
            limits.global_temp_phone_limit,
            global_temp_count,
            f"Barrier has reached the global limit of {limits.global_temp_phone_limit} temporary phone numbers.",
        )
    elif phone_type == BarrierPhone.PhoneType.SCHEDULE:
        user_schedule_count = existing_phones.filter(user=user, type=phone_type).count()
        global_schedule_count = existing_phones.filter(type=phone_type).count()

        validate_limit(
            limits.user_schedule_phone_limit,
            user_schedule_count,
            f"User has reached the limit of {limits.user_schedule_phone_limit} schedule phone numbers.",
        )
        validate_limit(
            limits.global_schedule_phone_limit,
            global_schedule_count,
            f"Barrier has reached the global limit of {limits.global_schedule_phone_limit} schedule phone numbers.",
        )
