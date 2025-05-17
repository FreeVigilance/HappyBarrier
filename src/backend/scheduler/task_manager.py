import logging
from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.utils.timezone import localtime, now

from action_history.models import BarrierActionLog
from phones.constants import MINIMUM_TIME_INTERVAL_MINUTES
from phones.models import BarrierPhone, ScheduleTimeInterval
from scheduler.jobs import schedule_cron_sms, schedule_once_sms
from scheduler.scheduler import get_scheduler
from scheduler.utils import JobAction, generate_job_id, parse_job_id

logger = logging.getLogger(__name__)

DELETE_PHONE_AFTER_SCHEDULING_MINUTES = 20
ACCESS_OPENING_SHIFT = timedelta(minutes=MINIMUM_TIME_INTERVAL_MINUTES - 1)


class PhoneTaskManager:
    def __init__(self, phone: BarrierPhone, log: BarrierActionLog):
        self.phone = phone
        self.scheduler = get_scheduler()
        self.log = log

    def add_tasks(self, mode: str = "add"):
        if self.phone.type == BarrierPhone.PhoneType.TEMPORARY:
            self._schedule_temporary_tasks()
        elif self.phone.type == BarrierPhone.PhoneType.SCHEDULE:
            self._schedule_schedule_tasks()
        self.sync_access(mode)

    def edit_tasks(self):
        self.cancel_all_tasks()
        self.add_tasks("edit")

    def delete_tasks(self):
        self.cancel_all_tasks()
        self.sync_access("delete")

    def cancel_all_tasks(self):
        logger.info(f"Cancelling all tasks for phone: {self.phone.id}")

        for job in self.scheduler.get_jobs():
            try:
                job_meta = parse_job_id(job.id)
            except ValidationError:
                continue
            if job_meta["phone_id"] == self.phone.id:
                self.scheduler.remove_job(job.id)

    def is_in_active_interval(self, current_dt: datetime) -> bool:
        adjusted_dt = current_dt + ACCESS_OPENING_SHIFT
        adjusted_time = adjusted_dt.time()
        current_time = current_dt.replace(second=0, microsecond=0).time()
        current_weekday = current_dt.strftime("%A").lower()

        if self.phone.type == BarrierPhone.PhoneType.TEMPORARY:
            return self.phone.start_time <= adjusted_dt and current_dt <= self.phone.end_time

        return self.phone.schedule_intervals.filter(
            day=current_weekday,
            start_time__lte=adjusted_time,
            end_time__gte=current_time,
        ).exists()

    def sync_access(self, mode: str):
        from message_management.services import SMSService

        if self.phone.type not in [BarrierPhone.PhoneType.SCHEDULE, BarrierPhone.PhoneType.TEMPORARY]:
            return

        current_dt = localtime(now())
        in_interval = self.is_in_active_interval(current_dt)
        logger.debug(f"In active interval: {in_interval}")

        if in_interval and mode in ["add", "edit"]:
            logger.info(f"Access should be OPEN — sending open command for phone {self.phone.id}")
            SMSService.send_add_phone_command(self.phone, self.log)

        if (in_interval and mode == "delete") or (not in_interval and mode == "edit"):
            logger.info(f"Access should be CLOSED — sending close command for phone {self.phone.id}")
            SMSService.send_delete_phone_command(self.phone, self.log)

    def _schedule_temporary_tasks(self):
        logger.info(f"Scheduling temporary tasks for phone: {self.phone.id}")

        if not self.phone.start_time or not self.phone.end_time:
            raise ValidationError("Temporary phones must have both start_time and end_time.")

        open_time = self.phone.start_time - ACCESS_OPENING_SHIFT
        open_job_id = generate_job_id(JobAction.OPEN, self.phone.id, BarrierPhone.PhoneType.TEMPORARY)
        schedule_once_sms(self.phone, JobAction.OPEN, open_job_id, run_time=open_time, log=self.log)

        close_job_id = generate_job_id(JobAction.CLOSE, self.phone.id, BarrierPhone.PhoneType.TEMPORARY)
        schedule_once_sms(self.phone, JobAction.CLOSE, close_job_id, run_time=self.phone.end_time, log=self.log)

        delete_time = self.phone.end_time + timedelta(minutes=DELETE_PHONE_AFTER_SCHEDULING_MINUTES)
        delete_job_id = generate_job_id(JobAction.DELETE, self.phone.id, BarrierPhone.PhoneType.TEMPORARY)
        schedule_once_sms(self.phone, JobAction.DELETE, delete_job_id, run_time=delete_time, log=None)

    def _schedule_schedule_tasks(self):
        logger.info(f"Scheduling schedule tasks for phone: {self.phone.id}")

        def _shift_day_back(day: str) -> str:
            days = list(ScheduleTimeInterval.DayOfWeek.values)
            idx = days.index(day)
            return days[(idx - 1) % 7]

        for interval in self.phone.schedule_intervals.all():
            day = interval.day

            open_time = (datetime.combine(datetime.today(), interval.start_time) - ACCESS_OPENING_SHIFT).time()
            open_day = _shift_day_back(day) if open_time > interval.start_time else day
            open_job_id = generate_job_id(
                JobAction.OPEN, self.phone.id, BarrierPhone.PhoneType.SCHEDULE, day=open_day, time_=open_time
            )
            schedule_cron_sms(self.phone, JobAction.OPEN, open_job_id, day=open_day, time_=open_time, log=self.log)

            close_time = interval.end_time

            close_job_id = generate_job_id(
                JobAction.CLOSE, self.phone.id, BarrierPhone.PhoneType.SCHEDULE, day=day, time_=close_time
            )
            schedule_cron_sms(self.phone, JobAction.CLOSE, close_job_id, day=day, time_=close_time, log=self.log)
