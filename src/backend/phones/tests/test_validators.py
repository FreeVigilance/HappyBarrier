from datetime import timedelta

import pytest
from django.utils.timezone import now
from rest_framework.exceptions import ValidationError

from barriers.models import BarrierLimit
from core.utils import ConflictError
from phones.constants import MINIMUM_TIME_INTERVAL_MINUTES
from phones.models import BarrierPhone
from phones.validators import validate_limits, validate_schedule_phone, validate_temporary_phone


@pytest.mark.django_db
class TestValidateTemporaryPhone:
    def test_valid_temporary_phone(self):
        start = now() + timedelta(minutes=MINIMUM_TIME_INTERVAL_MINUTES + 1)
        end = start + timedelta(minutes=MINIMUM_TIME_INTERVAL_MINUTES + 1)
        validate_temporary_phone(BarrierPhone.PhoneType.TEMPORARY, start, end)

    @pytest.mark.parametrize(
        "start_time, end_time",
        [
            (None, None),
            (None, now() + timedelta(minutes=10)),
            (now() + timedelta(minutes=10), None),
        ],
    )
    def test_missing_times(self, start_time, end_time):
        with pytest.raises(ValidationError) as exc:
            validate_temporary_phone(BarrierPhone.PhoneType.TEMPORARY, start_time, end_time)
        assert exc.value.detail["time"] == "start_time and end_time are required for temporary phone."

    def test_start_time_too_early(self):
        start = now()
        end = start + timedelta(minutes=MINIMUM_TIME_INTERVAL_MINUTES + 1)

        with pytest.raises(ValidationError) as exc:
            validate_temporary_phone(BarrierPhone.PhoneType.TEMPORARY, start, end)
        expected = f"start_time must be at least {MINIMUM_TIME_INTERVAL_MINUTES} minutes in the future."
        assert exc.value.detail["start_time"] == expected

    def test_end_time_before_start_time(self):
        start = now() + timedelta(minutes=MINIMUM_TIME_INTERVAL_MINUTES + 1)
        end = start - timedelta(minutes=1)

        with pytest.raises(ValidationError) as exc:
            validate_temporary_phone(BarrierPhone.PhoneType.TEMPORARY, start, end)
        assert exc.value.detail["end_time"] == "end_time must be after start_time."

    def test_short_interval(self):
        start = now() + timedelta(minutes=MINIMUM_TIME_INTERVAL_MINUTES + 1)
        end = start + timedelta(minutes=MINIMUM_TIME_INTERVAL_MINUTES - 1)

        with pytest.raises(ValidationError) as exc:
            validate_temporary_phone(BarrierPhone.PhoneType.TEMPORARY, start, end)
        assert exc.value.detail["time"] == f"Interval must be at least {MINIMUM_TIME_INTERVAL_MINUTES} minutes long."

    def test_non_temporary_with_times(self):
        with pytest.raises(ValidationError) as exc:
            validate_temporary_phone(BarrierPhone.PhoneType.PERMANENT, now(), now())
        assert exc.value.detail["time"] == "start_time and end_time are only allowed for temporary phone numbers."


@pytest.mark.django_db
class TestValidateSchedulePhone:
    def test_valid_schedule_phone(self, barrier):
        schedule = {"monday": [{"start_time": "08:00", "end_time": "10:00"}]}
        validate_schedule_phone(BarrierPhone.PhoneType.SCHEDULE, schedule, barrier)

    def test_missing_schedule(self, barrier):
        with pytest.raises(ValidationError) as exc:
            validate_schedule_phone(BarrierPhone.PhoneType.SCHEDULE, None, barrier)
        assert exc.value.detail["schedule"] == "Schedule is required for schedule phone type."

    def test_missing_intervals(self, barrier):
        schedule = {"monday": [], "tuesday": []}
        with pytest.raises(ValidationError) as exc:
            validate_schedule_phone(BarrierPhone.PhoneType.SCHEDULE, schedule, barrier)
        assert exc.value.detail["schedule"] == "Schedule must contain at least one interval."

    def test_schedule_exceeds_limit(self, barrier):
        BarrierLimit.objects.create(barrier=barrier, schedule_interval_limit=1)
        schedule = {"monday": [{"start": "08:00", "end": "09:00"}, {"start": "09:30", "end": "10:00"}]}
        with pytest.raises(ConflictError) as exc:
            validate_schedule_phone(BarrierPhone.PhoneType.SCHEDULE, schedule, barrier)
        assert exc.value.detail == "Phone schedule exceeds allowed number of intervals (1 max)."

    def test_schedule_not_allowed_for_non_schedule_type(self, barrier):
        schedule = {"monday": [{"start": "08:00", "end": "10:00"}]}
        with pytest.raises(ValidationError) as exc:
            validate_schedule_phone(BarrierPhone.PhoneType.PERMANENT, schedule, barrier)
        assert exc.value.detail["schedule"] == "Schedule is only allowed for schedule phone type."


@pytest.mark.django_db
class TestValidateLimits:
    def test_exceeds_user_limit(self, barrier, user):
        BarrierLimit.objects.create(barrier=barrier, user_phone_limit=0)

        with pytest.raises(ConflictError) as exc:
            validate_limits(BarrierPhone.PhoneType.PERMANENT, barrier, user)
        assert exc.value.detail == "User has reached the limit of 0 phone numbers."

    def test_exceeds_temp_limits(self, barrier, user):
        BarrierLimit.objects.create(barrier=barrier, user_temp_phone_limit=0, global_temp_phone_limit=0)
        BarrierPhone.objects.create(
            user=user,
            barrier=barrier,
            phone="+79000000001",
            type=BarrierPhone.PhoneType.TEMPORARY,
            device_serial_number=1,
        )

        with pytest.raises(ConflictError) as exc:
            validate_limits(BarrierPhone.PhoneType.TEMPORARY, barrier, user)
        assert exc.value.detail == "User has reached the limit of 0 temporary phone numbers."

    def test_exceeds_schedule_limits(self, barrier, user):
        BarrierLimit.objects.create(barrier=barrier, user_schedule_phone_limit=0, global_schedule_phone_limit=0)
        BarrierPhone.objects.create(
            barrier=barrier,
            user=user,
            type=BarrierPhone.PhoneType.SCHEDULE,
            phone="+79000000002",
            device_serial_number=2,
        )
        with pytest.raises(ConflictError) as exc:
            validate_limits(BarrierPhone.PhoneType.SCHEDULE, barrier, user)
        assert exc.value.detail == "User has reached the limit of 0 schedule phone numbers."
        assert "schedule phone numbers" in str(exc.value)

    def test_no_limits_set_does_not_raise(self, barrier, user):
        BarrierLimit.objects.create(barrier=barrier)
        validate_limits(BarrierPhone.PhoneType.PERMANENT, barrier, user)
        validate_limits(BarrierPhone.PhoneType.TEMPORARY, barrier, user)
        validate_limits(BarrierPhone.PhoneType.SCHEDULE, barrier, user)
