from datetime import time

import pytest
from django.core.exceptions import ValidationError

from phones.models import BarrierPhone, ScheduleTimeInterval
from scheduler.utils import JobAction, generate_job_id, parse_job_id


class TestGenerateJobId:
    def test_generate_temporary_job_id(self):
        job_id = generate_job_id(action=JobAction.OPEN, phone_id=123, phone_type=BarrierPhone.PhoneType.TEMPORARY)
        expected = "temporary_open_123"
        assert job_id == expected

    def test_generate_schedule_job_id(self):
        job_id = generate_job_id(
            action=JobAction.CLOSE,
            phone_id=456,
            phone_type=BarrierPhone.PhoneType.SCHEDULE,
            day=ScheduleTimeInterval.DayOfWeek.TUESDAY,
            time_=time(9, 30),
        )
        assert job_id == "schedule_close_456_tuesday_0930"

    def test_generate_schedule_job_id_missing_day_or_time(self):
        with pytest.raises(ValidationError, match="Day and time are required for schedule-based jobs."):
            generate_job_id(
                action=JobAction.CLOSE, phone_id=456, phone_type=BarrierPhone.PhoneType.SCHEDULE, time_=time(9, 30)
            )

    def test_generate_job_id_invalid_type(self):
        with pytest.raises(ValidationError, match="Phone type must be SCHEDULE or TEMPORARY."):
            generate_job_id(
                action=JobAction.CLOSE,
                phone_id=789,
                phone_type=BarrierPhone.PhoneType.PERMANENT,
            )

    def test_generate_schedule_delete_job_id_not_allowed(self):
        with pytest.raises(ValidationError, match="Cannot delete schedule-based jobs."):
            generate_job_id(
                action=JobAction.DELETE,
                phone_id=789,
                phone_type=BarrierPhone.PhoneType.SCHEDULE,
                day=ScheduleTimeInterval.DayOfWeek.THURSDAY,
                time_=time(12, 0),
            )


class TestParseJobId:
    def test_parse_temporary_job_id(self):
        job_id = "temporary_open_321"
        result = parse_job_id(job_id)

        assert result["phone_type"] == BarrierPhone.PhoneType.TEMPORARY
        assert result["action"] == JobAction.OPEN
        assert result["phone_id"] == 321
        assert result["day"] is None
        assert result["time"] is None

    def test_parse_schedule_job_id(self):
        job_id = "schedule_close_654_monday_0930"
        result = parse_job_id(job_id)

        assert result["phone_type"] == BarrierPhone.PhoneType.SCHEDULE
        assert result["action"] == JobAction.CLOSE
        assert result["phone_id"] == 654
        assert result["day"] == "monday"
        assert result["time"] == time(9, 30)

    def test_parse_invalid_job_id_format(self):
        with pytest.raises(ValidationError, match="Invalid job ID format"):
            parse_job_id("bad_format_id")

    def test_parse_invalid_job_type(self):
        with pytest.raises(ValidationError, match="Invalid job ID format"):
            parse_job_id("permanent_open_123_123456")
