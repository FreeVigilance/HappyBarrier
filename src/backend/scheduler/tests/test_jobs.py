from datetime import datetime, time, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from apscheduler.jobstores.base import JobLookupError
from django.core.exceptions import ValidationError

from phones.models import ScheduleTimeInterval
from scheduler.jobs import cancel_job, schedule_cron_sms, schedule_once_sms
from scheduler.utils import JobAction


@pytest.mark.django_db
class TestScheduleOnceSms:
    @patch("scheduler.jobs.get_scheduler")
    @patch("scheduler.jobs.send_open_sms")
    def test_schedule_open_once_sms(self, mock_send_open_sms, mock_get_scheduler, barrier_phone):
        phone, log = barrier_phone

        mock_scheduler = MagicMock()
        mock_get_scheduler.return_value = mock_scheduler

        run_time = datetime.now(timezone.utc) + timedelta(minutes=10)
        job_id = "temporary_open_1_123456"

        schedule_once_sms(phone, JobAction.OPEN, job_id, run_time, log)

        mock_scheduler.add_job.assert_called_once()
        kwargs = mock_scheduler.add_job.call_args.kwargs
        assert kwargs["id"] == job_id
        assert kwargs["run_date"] == run_time
        assert kwargs["trigger"] == "date"

        args = mock_scheduler.add_job.call_args.kwargs["args"]
        assert args[0] == phone
        assert args[1] == log

    @patch("scheduler.jobs.get_scheduler")
    def test_schedule_once_sms_invalid_action(self, mock_get_scheduler, barrier_phone):
        phone, log = barrier_phone
        run_time = datetime.now(timezone.utc)
        with pytest.raises(ValidationError):
            schedule_once_sms(phone, "invalid", "job_id", run_time, log)


@pytest.mark.django_db
class TestScheduleCronSms:
    @patch("scheduler.jobs.get_scheduler")
    @patch("scheduler.jobs.send_close_sms")
    def test_schedule_weekly_close_sms(self, mock_send_close_sms, mock_get_scheduler, barrier_phone):
        phone, log = barrier_phone

        mock_scheduler = MagicMock()
        mock_get_scheduler.return_value = mock_scheduler

        job_id = "schedule_close_1_monday_0930"

        schedule_cron_sms(
            phone=phone,
            action=JobAction.CLOSE,
            job_id=job_id,
            day=ScheduleTimeInterval.DayOfWeek.MONDAY,
            time_=time(9, 30),
            log=log,
        )

        mock_scheduler.add_job.assert_called_once()
        kwargs = mock_scheduler.add_job.call_args.kwargs
        assert kwargs["day_of_week"] == "mon"
        assert kwargs["hour"] == 9
        assert kwargs["minute"] == 30
        assert kwargs["trigger"] == "cron"

        args = mock_scheduler.add_job.call_args.kwargs["args"]
        assert args[0] == phone
        assert args[1] == log

    @patch("scheduler.jobs.get_scheduler")
    def test_schedule_cron_sms_invalid_action(self, mock_get_scheduler, barrier_phone):
        phone, log = barrier_phone
        with pytest.raises(ValidationError):
            schedule_cron_sms(
                phone=phone,
                action="invalid",
                job_id="some_id",
                day=ScheduleTimeInterval.DayOfWeek.FRIDAY,
                time_=time(10, 0),
                log=log,
            )


class TestCancelJob:
    @patch("scheduler.jobs.get_scheduler")
    def test_cancel_existing_job(self, mock_get_scheduler):
        mock_scheduler = MagicMock()
        mock_get_scheduler.return_value = mock_scheduler

        cancel_job("job_to_cancel")

        mock_scheduler.remove_job.assert_called_once_with("job_to_cancel")

    @patch("scheduler.jobs.get_scheduler")
    def test_cancel_nonexistent_job_logs_warning(self, mock_get_scheduler):
        mock_scheduler = MagicMock()
        mock_scheduler.remove_job.side_effect = JobLookupError("Job not found")
        mock_get_scheduler.return_value = mock_scheduler

        cancel_job("missing_job")  # Should not raise
