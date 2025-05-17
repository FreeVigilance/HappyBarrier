import logging
from datetime import datetime, time

from apscheduler.jobstores.base import ConflictingIdError, JobLookupError
from django.core.exceptions import ValidationError

from action_history.models import BarrierActionLog
from phones.constants import MINIMUM_TIME_INTERVAL_MINUTES
from phones.models import BarrierPhone, ScheduleTimeInterval
from scheduler.scheduler import get_scheduler
from scheduler.tasks import send_close_sms, send_delete_phone, send_open_sms
from scheduler.utils import JobAction

logger = logging.getLogger(__name__)


def schedule_once_sms(
    phone: BarrierPhone, action: JobAction, job_id: str, run_time: datetime, log: BarrierActionLog | None
):
    """Schedules a one-time OPEN, CLOSE or DELETE SMS command at the specified datetime."""

    scheduler = get_scheduler()

    func = {
        JobAction.OPEN: send_open_sms,
        JobAction.CLOSE: send_close_sms,
        JobAction.DELETE: send_delete_phone,
    }.get(action)

    if not func:
        raise ValidationError(f"Unsupported JobAction: {action}")

    try:
        scheduler.add_job(
            func=func,
            trigger="date",
            run_date=run_time,
            args=[phone, log],
            id=job_id,
            replace_existing=True,
            misfire_grace_time=MINIMUM_TIME_INTERVAL_MINUTES * 60,  # TODO - customise for task
        )
        logger.info(f"Scheduled {action.value.upper()} SMS for phone {phone.id} at {run_time} (job_id={job_id})")
    except ConflictingIdError:
        logger.warning(
            f"Conflict when scheduling {action.value.upper()} SMS for phone {phone.id}. "
            f"Job ID {job_id} already exists."
        )
        raise
    except Exception as e:
        logger.exception(f"Failed to schedule {action.value.upper()} SMS for phone {phone.id}: {str(e)}")
        raise


def apscheduler_day_of_week(day: ScheduleTimeInterval.DayOfWeek) -> str:
    """Convert 'monday' → 'mon', etc., for APScheduler cron trigger."""

    day_map = {
        ScheduleTimeInterval.DayOfWeek.MONDAY: "mon",
        ScheduleTimeInterval.DayOfWeek.TUESDAY: "tue",
        ScheduleTimeInterval.DayOfWeek.WEDNESDAY: "wed",
        ScheduleTimeInterval.DayOfWeek.THURSDAY: "thu",
        ScheduleTimeInterval.DayOfWeek.FRIDAY: "fri",
        ScheduleTimeInterval.DayOfWeek.SATURDAY: "sat",
        ScheduleTimeInterval.DayOfWeek.SUNDAY: "sun",
    }
    return day_map[day]


def schedule_cron_sms(
    phone: BarrierPhone,
    action: JobAction,
    job_id: str,
    day: ScheduleTimeInterval.DayOfWeek,
    time_: time,
    log: BarrierActionLog,
):
    """Schedules a weekly OPEN or CLOSE SMS command at the given time."""

    scheduler = get_scheduler()

    func = {
        JobAction.OPEN: send_open_sms,
        JobAction.CLOSE: send_close_sms,
    }.get(action)

    if not func:
        raise ValidationError(f"Unsupported JobAction: {action}")

    try:
        scheduler.add_job(
            func=func,
            trigger="cron",
            day_of_week=apscheduler_day_of_week(day),
            hour=time_.hour,
            minute=time_.minute,
            args=[phone, log],
            id=job_id,
            replace_existing=True,
        )
        logger.info(
            f"Scheduled weekly {action.value.upper()} SMS for phone {phone.id} on {day} at {time_} (job_id={job_id})"
        )
    except ConflictingIdError:
        logger.warning(
            f"Conflict when scheduling weekly {action.value.upper()} SMS for phone {phone.id}. "
            f"Job ID {job_id} already exists."
        )
        raise
    except Exception as e:
        logger.exception(f"Failed to schedule weekly {action.value.upper()} SMS for phone {phone.id}: {str(e)}")
        raise


def cancel_job(job_id: str):
    """Cancel a scheduled job by its ID, with safe error handling."""

    scheduler = get_scheduler()

    try:
        scheduler.remove_job(job_id)
        logger.info(f"Canceled job: {job_id}")
    except JobLookupError:
        logger.warning(f"Job not found for cancellation: {job_id}")
