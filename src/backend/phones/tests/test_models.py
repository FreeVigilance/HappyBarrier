import json
from datetime import datetime, time
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from django.core.exceptions import PermissionDenied
from rest_framework.exceptions import PermissionDenied as DRFPermissionDenied

from action_history.models import BarrierActionLog
from conftest import BARRIER_PERMANENT_PHONE, BARRIER_PERMANENT_PHONE_NAME, USER_PHONE
from core.utils import ConflictError
from message_management.services import SMSService
from phones.models import BarrierPhone, ScheduleTimeInterval


@pytest.mark.django_db
class TestBarrierPhoneModel:
    @pytest.fixture
    def create_barrier_phone_obj(self):
        """Factory fixture to create a barrier phone entry"""

        def _create_barrier_phone(
            user,
            barrier,
            phone=BARRIER_PERMANENT_PHONE,
            type=BarrierPhone.PhoneType.PERMANENT,
            name=BARRIER_PERMANENT_PHONE_NAME,
            device_serial_number=1,
            start_time=None,
            end_time=None,
        ):
            return BarrierPhone.objects.create(
                user=user,
                barrier=barrier,
                phone=phone,
                type=type,
                name=name,
                device_serial_number=device_serial_number,
                start_time=start_time,
                end_time=end_time,
            )

        return _create_barrier_phone

    def test_str(self, barrier_phone):
        barrier_phone, _ = barrier_phone
        assert str(barrier_phone) == f"Phone: {barrier_phone.phone} ({barrier_phone.user}, {barrier_phone.barrier})"

    class TestBarrierPhoneSerialNumber:
        def test_get_available_serial_number_returns_min_free(self, barrier, user, create_barrier_phone_obj):
            barrier.device_phones_amount = 4
            barrier.save()
            create_barrier_phone_obj(user, barrier)
            create_barrier_phone_obj(
                user, barrier, phone=USER_PHONE, type=BarrierPhone.PhoneType.PRIMARY, device_serial_number=3
            )

            assert BarrierPhone.get_available_serial_number(barrier) == 2

        def test_get_available_serial_number_returns_none(self, barrier, user, create_barrier_phone_obj):
            barrier.device_phones_amount = 2
            barrier.save()
            create_barrier_phone_obj(user, barrier)
            create_barrier_phone_obj(
                user, barrier, phone=USER_PHONE, type=BarrierPhone.PhoneType.PRIMARY, device_serial_number=2
            )

            assert BarrierPhone.get_available_serial_number(barrier) is None

    class TestDescribePhoneParams:
        def test_primary_phone_description(self, user, barrier, create_barrier_phone):
            phone, _ = create_barrier_phone(
                user, barrier, phone=user.phone, type=BarrierPhone.PhoneType.PRIMARY, name="John's phone"
            )
            data = json.loads(phone.describe_phone_params())
            assert data["name"] == "John's phone"
            assert data["type"] == BarrierPhone.PhoneType.PRIMARY

        def test_permanent_phone_description(self, user, barrier, create_barrier_phone):
            phone, _ = create_barrier_phone(user, barrier, type=BarrierPhone.PhoneType.PERMANENT, name="John's phone")
            data = json.loads(phone.describe_phone_params())
            assert data["name"] == "John's phone"
            assert data["type"] == BarrierPhone.PhoneType.PERMANENT

        @patch("phones.validators.now")
        def test_temporary_phone_description(self, mock_now, user, barrier, create_barrier_phone):
            mock_now.return_value = datetime(2025, 5, 5, 11, 0, tzinfo=ZoneInfo("Europe/Moscow"))
            start = datetime(2025, 5, 5, 12, 0, tzinfo=ZoneInfo("Europe/Moscow"))
            end = datetime(2025, 5, 5, 14, 0, tzinfo=ZoneInfo("Europe/Moscow"))
            phone, _ = create_barrier_phone(
                user, barrier, type=BarrierPhone.PhoneType.TEMPORARY, start_time=start, end_time=end, name="Temp"
            )
            data = json.loads(phone.describe_phone_params())
            assert data["type"] == BarrierPhone.PhoneType.TEMPORARY
            assert data["start_time"] == "2025-05-05T12:00+03:00"
            assert data["end_time"] == "2025-05-05T14:00+03:00"

        def test_schedule_phone_description(self, user, barrier, create_barrier_phone):
            schedule = {
                "monday": [
                    {"start_time": time(9, 0), "end_time": time(10, 0)},
                    {"start_time": time(11, 0), "end_time": time(12, 0)},
                ]
            }
            phone, _ = create_barrier_phone(
                user, barrier, type=BarrierPhone.PhoneType.SCHEDULE, schedule=schedule, name="Scheduled"
            )
            data = json.loads(phone.describe_phone_params())
            assert data["type"] == BarrierPhone.PhoneType.SCHEDULE
            assert "monday" in data["schedule"]
            assert data["schedule"]["monday"] == [
                {"start_time": "09:00", "end_time": "10:00"},
                {"start_time": "11:00", "end_time": "12:00"},
            ]

    @pytest.mark.django_db
    class TestBarrierPhoneSendSMSCreate:
        @patch.object(SMSService, "send_add_phone_command")
        def test_send_sms_to_create_primary_calls_sms(self, mock_send, barrier_phone):
            barrier_phone, log = barrier_phone
            barrier_phone.type = BarrierPhone.PhoneType.PRIMARY
            barrier_phone.send_sms_to_create(log)
            mock_send.assert_called_once_with(barrier_phone, log)

        @patch.object(SMSService, "send_add_phone_command")
        def test_send_sms_to_create_permanent_calls_sms(self, mock_send, barrier_phone):
            barrier_phone, log = barrier_phone
            barrier_phone.type = BarrierPhone.PhoneType.PERMANENT
            barrier_phone.send_sms_to_create(log)
            mock_send.assert_called_once_with(barrier_phone, log)

        @patch("scheduler.task_manager.PhoneTaskManager")
        def test_send_sms_to_create_temporary_schedules_task(self, mock_task_manager_class, barrier_phone):
            barrier_phone, log = barrier_phone
            barrier_phone.type = BarrierPhone.PhoneType.TEMPORARY

            mock_task_manager = mock_task_manager_class.return_value

            barrier_phone.send_sms_to_create(log)

            mock_task_manager_class.assert_called_once_with(barrier_phone, log)
            mock_task_manager.add_tasks.assert_called_once_with()

        @patch("scheduler.task_manager.PhoneTaskManager")
        def test_send_sms_to_create_schedule_schedules_task(self, mock_task_manager_class, barrier_phone):
            barrier_phone, log = barrier_phone
            barrier_phone.type = BarrierPhone.PhoneType.SCHEDULE

            mock_task_manager = mock_task_manager_class.return_value

            barrier_phone.send_sms_to_create(log)

            mock_task_manager_class.assert_called_once_with(barrier_phone, log)
            mock_task_manager.add_tasks.assert_called_once_with()

    @pytest.mark.django_db
    class TestBarrierPhoneSendSMSDelete:
        @patch.object(SMSService, "send_delete_phone_command")
        def test_send_sms_to_delete_primary_calls_sms(self, mock_send, barrier_phone):
            barrier_phone, log = barrier_phone
            barrier_phone.type = BarrierPhone.PhoneType.PRIMARY
            barrier_phone.send_sms_to_delete(log)
            mock_send.assert_called_once_with(barrier_phone, log)

        @patch.object(SMSService, "send_delete_phone_command")
        def test_send_sms_to_delete_permanent_calls_sms(self, mock_send, barrier_phone):
            barrier_phone, log = barrier_phone
            barrier_phone.type = BarrierPhone.PhoneType.PERMANENT
            barrier_phone.send_sms_to_delete(log)
            mock_send.assert_called_once_with(barrier_phone, log)

        @patch("scheduler.task_manager.PhoneTaskManager.delete_tasks")
        def test_send_sms_to_delete_temporary_schedules_task(self, mock_delete_tasks, barrier_phone):
            barrier_phone, log = barrier_phone
            barrier_phone.type = BarrierPhone.PhoneType.TEMPORARY
            barrier_phone.send_sms_to_delete(log)
            mock_delete_tasks.assert_called_once()

        @patch("scheduler.task_manager.PhoneTaskManager.delete_tasks")
        def test_send_sms_to_delete_schedule_schedules_task(self, mock_delete_tasks, barrier_phone):
            barrier_phone, log = barrier_phone
            barrier_phone.type = BarrierPhone.PhoneType.SCHEDULE
            barrier_phone.send_sms_to_delete(log)
            mock_delete_tasks.assert_called_once()

    class TestBarrierPhoneRemoval:
        def test_delete_raises_error(self, barrier_phone):
            phone, _ = barrier_phone
            with pytest.raises(PermissionDenied):
                phone.delete()

        def test_remove_sets_inactive(self, barrier_phone):
            phone, _ = barrier_phone
            phone.remove(author=BarrierActionLog.Author.USER, reason=BarrierActionLog.Reason.BARRIER_EXIT)
            assert not phone.is_active

        def test_remove_creates_log_and_deactivates(self, barrier_phone):
            phone, _ = barrier_phone

            phone, log = phone.remove(author=BarrierActionLog.Author.USER, reason=BarrierActionLog.Reason.BARRIER_EXIT)

            assert not phone.is_active
            assert log.phone == phone
            assert log.reason == BarrierActionLog.Reason.BARRIER_EXIT
            assert log.action_type == BarrierActionLog.ActionType.DELETE_PHONE

    class TestBarrierPhoneCreate:
        def test_create_duplicate_phone_raises(self, user, barrier):
            BarrierPhone.create(
                user=user, barrier=barrier, phone=BARRIER_PERMANENT_PHONE, type=BarrierPhone.PhoneType.PERMANENT
            )
            with pytest.raises(ConflictError) as exc:
                BarrierPhone.create(
                    user=user, barrier=barrier, phone=BARRIER_PERMANENT_PHONE, type=BarrierPhone.PhoneType.PERMANENT
                )
            assert exc.value.detail == "Phone already exists for this user in the barrier."

        def test_create_primary_duplicate_raises(self, user, barrier):
            BarrierPhone.create(user=user, barrier=barrier, phone=user.phone, type=BarrierPhone.PhoneType.PRIMARY)
            with pytest.raises(ConflictError) as exc:
                BarrierPhone.create(
                    user=user, barrier=barrier, phone="+79990001122", type=BarrierPhone.PhoneType.PRIMARY
                )
            assert exc.value.detail == "User already has a primary phone number in this barrier."

        def test_create_primary_with_wrong_number_raises(self, user, barrier):
            with pytest.raises(DRFPermissionDenied) as exc:
                BarrierPhone.create(
                    user=user, barrier=barrier, phone=BARRIER_PERMANENT_PHONE, type=BarrierPhone.PhoneType.PRIMARY
                )
            assert exc.value.detail == "Wrong phone given as primary. Primary phone should be users main number."

        @patch("phones.models.validate_limits")
        @patch("phones.models.validate_schedule_phone")
        @patch("phones.models.validate_temporary_phone")
        def test_validators_called(self, mock_temp, mock_sched, mock_limits, user, barrier):
            BarrierPhone.create(
                user=user, barrier=barrier, phone=BARRIER_PERMANENT_PHONE, type=BarrierPhone.PhoneType.PERMANENT
            )
            mock_limits.assert_called_once_with(BarrierPhone.PhoneType.PERMANENT, barrier, user)
            mock_temp.assert_called_once_with(BarrierPhone.PhoneType.PERMANENT, None, None)
            mock_sched.assert_called_once_with(BarrierPhone.PhoneType.PERMANENT, None, barrier)

        def test_create_fails_without_serial(self, user, barrier):
            barrier.device_phones_amount = 0
            barrier.save()
            with pytest.raises(ConflictError) as exc:
                BarrierPhone.create(user=user, barrier=barrier, phone=user.phone, type=BarrierPhone.PhoneType.PRIMARY)
            assert exc.value.detail == "Barrier has reached the maximum number of phone numbers."

        def test_create_schedule_creates_intervals(self, user, barrier):
            schedule = {
                "monday": [
                    {
                        "start_time": datetime.strptime("09:00", "%H:%M").time(),
                        "end_time": datetime.strptime("10:00", "%H:%M").time(),
                    }
                ]
            }
            phone, log = BarrierPhone.create(
                user=user,
                barrier=barrier,
                phone=BARRIER_PERMANENT_PHONE,
                type=BarrierPhone.PhoneType.SCHEDULE,
                schedule=schedule,
                author=BarrierActionLog.Author.SYSTEM,
                reason=BarrierActionLog.Reason.MANUAL,
            )

            assert ScheduleTimeInterval.objects.filter(phone=phone).exists()
            assert log.phone == phone
            assert log.barrier == barrier
            assert log.author == BarrierActionLog.Author.SYSTEM
            assert log.action_type == BarrierActionLog.ActionType.ADD_PHONE
            assert log.reason == BarrierActionLog.Reason.MANUAL
            data = json.loads(log.new_value)
            assert data["type"] == "schedule"
            assert "schedule" in data
            assert "monday" in data["schedule"]


@pytest.mark.django_db
class TestScheduleTimeIntervalModel:
    def test_str_representation(self, schedule_barrier_phone):
        phone, _ = schedule_barrier_phone
        interval = ScheduleTimeInterval.objects.filter(phone=phone).first()
        expected = f"'{phone.phone}': {interval.day} {interval.start_time}-{interval.end_time}"
        assert str(interval) == expected

    def test_create_schedule_creates_intervals(self, schedule_barrier_phone):
        phone, _ = schedule_barrier_phone
        ScheduleTimeInterval.objects.filter(phone=phone).delete()

        schedule_data = {
            "monday": [
                {"start_time": time(9, 0), "end_time": time(10, 0)},
                {"start_time": time(11, 0), "end_time": time(12, 0)},
            ],
            "friday": [
                {"start_time": time(13, 0), "end_time": time(14, 0)},
            ],
        }

        ScheduleTimeInterval.create_schedule(phone, schedule_data)

        intervals = ScheduleTimeInterval.objects.filter(phone=phone)
        assert intervals.count() == 3
        days = {i.day for i in intervals}
        assert days == {"monday", "friday"}

    def test_replace_schedule_replaces_intervals(self, schedule_barrier_phone):
        phone, _ = schedule_barrier_phone

        assert ScheduleTimeInterval.objects.filter(phone=phone).count() == 2

        new_schedule = {
            "wednesday": [
                {"start_time": time(13, 0), "end_time": time(14, 0)},
                {"start_time": time(15, 0), "end_time": time(16, 0)},
            ]
        }

        ScheduleTimeInterval.replace_schedule(phone, new_schedule)

        intervals = ScheduleTimeInterval.objects.filter(phone=phone)
        assert intervals.count() == 2
        days = set(i.day for i in intervals)
        assert days == {"wednesday"}
        times = [(i.start_time, i.end_time) for i in intervals]
        assert (time(13, 0), time(14, 0)) in times
        assert (time(15, 0), time(16, 0)) in times

    def test_get_schedule_grouped_by_day(self, schedule_barrier_phone):
        phone, _ = schedule_barrier_phone
        grouped = ScheduleTimeInterval.get_schedule_grouped_by_day(phone)

        assert isinstance(grouped, dict)
        assert set(grouped.keys()) == set(ScheduleTimeInterval.DayOfWeek.values)

        days_with_intervals = {day for day, intervals in grouped.items() if intervals}
        assert days_with_intervals
        for intervals in grouped.values():
            for interval in intervals:
                assert "start_time" in interval
                assert "end_time" in interval
