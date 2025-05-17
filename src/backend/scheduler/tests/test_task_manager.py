from datetime import datetime, time, timedelta
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest
from django.core.exceptions import ValidationError
from django.utils.timezone import now

from message_management.services import SMSService
from phones.models import BarrierPhone
from scheduler.task_manager import ACCESS_OPENING_SHIFT, DELETE_PHONE_AFTER_SCHEDULING_MINUTES, PhoneTaskManager
from scheduler.utils import JobAction, generate_job_id


@pytest.mark.django_db
class TestAddTasks:
    @patch.object(PhoneTaskManager, "_schedule_temporary_tasks")
    @patch.object(PhoneTaskManager, "_schedule_schedule_tasks")
    @patch.object(PhoneTaskManager, "sync_access")
    def test_add_tasks_for_temporary_phone(
        self, mock_sync, mock_sched_schedule, mock_sched_temp, temporary_barrier_phone
    ):
        phone, log = temporary_barrier_phone
        manager = PhoneTaskManager(phone, log)
        manager.add_tasks()

        mock_sched_temp.assert_called_once()
        mock_sched_schedule.assert_not_called()
        mock_sync.assert_called_once_with("add")

    @patch.object(PhoneTaskManager, "_schedule_temporary_tasks")
    @patch.object(PhoneTaskManager, "_schedule_schedule_tasks")
    @patch.object(PhoneTaskManager, "sync_access")
    def test_add_tasks_for_schedule_phone(
        self, mock_sync, mock_sched_schedule, mock_sched_temp, schedule_barrier_phone
    ):
        phone, log = schedule_barrier_phone
        manager = PhoneTaskManager(phone, log)
        manager.add_tasks("edit")

        mock_sched_schedule.assert_called_once()
        mock_sched_temp.assert_not_called()
        mock_sync.assert_called_once_with("edit")


@pytest.mark.django_db
class TestEditTasks:
    @patch.object(PhoneTaskManager, "cancel_all_tasks")
    @patch.object(PhoneTaskManager, "add_tasks")
    def test_edit_flow(self, mock_add, mock_cancel, temporary_barrier_phone):
        phone, log = temporary_barrier_phone
        manager = PhoneTaskManager(phone, log)
        manager.edit_tasks()

        mock_cancel.assert_called_once()
        mock_add.assert_called_once_with("edit")


@pytest.mark.django_db
class TestDeleteTasks:
    @patch.object(PhoneTaskManager, "cancel_all_tasks")
    @patch.object(PhoneTaskManager, "sync_access")
    def test_delete_flow(self, mock_sync, mock_cancel, temporary_barrier_phone):
        phone, log = temporary_barrier_phone
        manager = PhoneTaskManager(phone, log)
        manager.delete_tasks()

        mock_cancel.assert_called_once()
        mock_sync.assert_called_once_with("delete")


@pytest.mark.django_db
class TestCancelAllTasks:
    @pytest.fixture
    def scheduler_mock(self):
        scheduler = MagicMock()
        with patch("scheduler.task_manager.get_scheduler", return_value=scheduler):
            yield scheduler

    def test_removes_matching_jobs(self, scheduler_mock, temporary_barrier_phone):
        phone, log = temporary_barrier_phone
        job_ids = [generate_job_id(action, phone.id, phone.type) for action in JobAction]
        jobs = [type("Job", (), {"id": id})() for id in job_ids]
        scheduler_mock.get_jobs.return_value = jobs

        manager = PhoneTaskManager(phone, log)
        manager.scheduler = scheduler_mock

        manager.cancel_all_tasks()

        scheduler_mock.remove_job.assert_any_call(jobs[0].id)
        scheduler_mock.remove_job.assert_any_call(jobs[1].id)


@pytest.mark.django_db
class TestIsInActiveInterval:
    class TestTemporaryPhone:
        def test_in_active_interval(self, create_barrier_phone, user, barrier):
            start = now() + timedelta(minutes=15)
            end = start + timedelta(minutes=30)
            current = start + timedelta(minutes=10)

            phone, log = create_barrier_phone(
                user, barrier, type=BarrierPhone.PhoneType.TEMPORARY, start_time=start, end_time=end
            )
            manager = PhoneTaskManager(phone, log)

            assert manager.is_in_active_interval(current) is True

        def test_outside_active_interval(self, create_barrier_phone, user, barrier):
            start = now() + timedelta(minutes=15)
            end = start + timedelta(minutes=30)
            current = start + timedelta(minutes=50)

            phone, log = create_barrier_phone(
                user, barrier, type=BarrierPhone.PhoneType.TEMPORARY, start_time=start, end_time=end
            )
            manager = PhoneTaskManager(phone, log)

            assert manager.is_in_active_interval(current) is False

    class TestSchedulePhone:
        def test_inside_schedule_interval(self, create_barrier_phone, user, barrier):
            schedule = {
                "monday": [
                    {
                        "start_time": time(11, 55),
                        "end_time": time(12, 10),
                    }
                ]
            }
            current = datetime(2025, 5, 5, 12, 0, tzinfo=ZoneInfo("Europe/Moscow"))  # Monday

            phone, log = create_barrier_phone(user, barrier, type="schedule", schedule=schedule)
            manager = PhoneTaskManager(phone, log)

            assert manager.is_in_active_interval(current) is True

        def test_outside_schedule_interval(self, create_barrier_phone, user, barrier):
            schedule = {
                "monday": [
                    {
                        "start_time": time(9, 0),
                        "end_time": time(10, 0),
                    }
                ]
            }
            current = datetime(2025, 5, 5, 12, 0, tzinfo=ZoneInfo("Europe/Moscow"))  # Monday

            phone, log = create_barrier_phone(user, barrier, type="schedule", schedule=schedule)
            manager = PhoneTaskManager(phone, log)

            assert manager.is_in_active_interval(current) is False


@pytest.mark.django_db
class TestSyncAccess:
    @patch.object(SMSService, "send_add_phone_command")
    @patch.object(SMSService, "send_delete_phone_command")
    @pytest.mark.parametrize(
        "in_interval,mode,expect_add,expect_delete",
        [
            # Should call send_add_phone_command
            (True, "add", True, False),
            (True, "edit", True, False),
            # Should call send_delete_phone_command
            (True, "delete", False, True),
            (False, "edit", False, True),
            # Should do nothing
            (False, "add", False, False),
            (False, "delete", False, False),
        ],
    )
    def test_sync_access_logic(
        self,
        mock_send_delete,
        mock_send_add,
        in_interval,
        mode,
        expect_add,
        expect_delete,
        schedule_barrier_phone,
        user,
        barrier,
    ):
        phone, log = schedule_barrier_phone
        manager = PhoneTaskManager(phone, log)

        manager.is_in_active_interval = MagicMock(return_value=in_interval)

        manager.sync_access(mode)

        if expect_add:
            mock_send_add.assert_called_once_with(phone, log)
        else:
            mock_send_add.assert_not_called()

        if expect_delete:
            mock_send_delete.assert_called_once_with(phone, log)
        else:
            mock_send_delete.assert_not_called()


@pytest.mark.django_db
class TestScheduleTemporaryTasks:
    @patch("scheduler.task_manager.schedule_once_sms")
    def test_schedules_all_tasks_with_correct_times(self, mock_schedule_once_sms, temporary_barrier_phone):
        phone, log = temporary_barrier_phone
        start_time = phone.start_time
        end_time = phone.end_time
        open_expected = start_time - ACCESS_OPENING_SHIFT
        delete_expected = end_time + timedelta(minutes=DELETE_PHONE_AFTER_SCHEDULING_MINUTES)

        manager = PhoneTaskManager(phone, log)
        manager._schedule_temporary_tasks()

        assert mock_schedule_once_sms.call_count == 3

        expected = {
            JobAction.OPEN: open_expected,
            JobAction.CLOSE: end_time,
            JobAction.DELETE: delete_expected,
        }

        for call in mock_schedule_once_sms.call_args_list:
            action = call.args[1]
            run_time = call.kwargs["run_time"]
            expected_msg = f"{action} has wrong run_time: expected {expected[action]}, got {run_time}"
            assert run_time == expected[action], expected_msg

    @patch("scheduler.task_manager.schedule_once_sms")
    def test_raises_if_start_or_end_time_missing(self, mock_schedule_once_sms, temporary_barrier_phone):
        phone, log = temporary_barrier_phone
        phone.start_time = None
        phone.end_time = None

        manager = PhoneTaskManager(phone, log)
        with pytest.raises(ValidationError, match="Temporary phones must have both start_time and end_time."):
            manager._schedule_temporary_tasks()


@pytest.mark.django_db
class TestScheduleScheduleTasks:
    @patch("scheduler.task_manager.schedule_cron_sms")
    def test_schedules_cron_tasks_with_shift(self, mock_schedule_cron_sms, create_barrier_phone, user, barrier):
        schedule = {"monday": [{"start_time": time(0, 1), "end_time": time(1, 0)}]}
        phone, log = create_barrier_phone(
            user, barrier, "BARRIER_SCHEDULE_PHONE", BarrierPhone.PhoneType.SCHEDULE, schedule=schedule
        )

        manager = PhoneTaskManager(phone, log)
        manager._schedule_schedule_tasks()

        assert mock_schedule_cron_sms.call_count == 2
        actions = [call.args[1] for call in mock_schedule_cron_sms.call_args_list]
        assert JobAction.OPEN in actions
        assert JobAction.CLOSE in actions

    @patch("scheduler.task_manager.schedule_cron_sms")
    def test_schedules_cron_tasks_without_shift(self, mock_schedule_cron_sms, create_barrier_phone, user, barrier):
        schedule = {"monday": [{"start_time": time(12, 0), "end_time": time(13, 0)}]}
        phone, log = create_barrier_phone(
            user, barrier, "BARRIER_SCHEDULE_PHONE", BarrierPhone.PhoneType.SCHEDULE, schedule=schedule
        )

        manager = PhoneTaskManager(phone, log)
        manager._schedule_schedule_tasks()

        assert mock_schedule_cron_sms.call_count == 2
        actions = [call.args[1] for call in mock_schedule_cron_sms.call_args_list]
        assert JobAction.OPEN in actions
        assert JobAction.CLOSE in actions
