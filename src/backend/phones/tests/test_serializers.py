import json
from datetime import date, datetime, time, timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.utils.timezone import localtime, now
from rest_framework import serializers
from rest_framework.exceptions import NotFound, PermissionDenied

from action_history.models import BarrierActionLog
from conftest import BARRIER_PERMANENT_PHONE
from phones.constants import MINIMUM_TIME_INTERVAL_MINUTES
from phones.models import BarrierPhone
from phones.serializers import (
    CreateBarrierPhoneSerializer,
    ScheduleSerializer,
    ScheduleTimeIntervalSerializer,
    UpdateBarrierPhoneSerializer,
    UpdatePhoneScheduleSerializer,
)


@pytest.mark.django_db
class TestScheduleTimeIntervalSerializer:
    def test_valid_interval(self):
        data = {"start_time": time(9, 0), "end_time": time(10, 0)}
        serializer = ScheduleTimeIntervalSerializer(data=data)

        assert serializer.is_valid(), serializer.errors

    def test_start_time_after_end_time(self):
        data = {"start_time": time(12, 0), "end_time": time(11, 0)}
        serializer = ScheduleTimeIntervalSerializer(data=data)

        assert not serializer.is_valid()
        assert serializer.errors["time"][0] == "end_time must be after start_time."

    def test_interval_too_short(self):
        start = time(10, 0)
        end = (datetime.combine(date.today(), start) + timedelta(minutes=MINIMUM_TIME_INTERVAL_MINUTES - 1)).time()
        data = {"start_time": start, "end_time": end}
        serializer = ScheduleTimeIntervalSerializer(data=data)

        assert not serializer.is_valid()
        expected = f"Interval must be at least {MINIMUM_TIME_INTERVAL_MINUTES} minutes long."
        assert serializer.errors["time"][0] == expected


@pytest.mark.django_db
class TestScheduleSerializer:
    def test_empty_day_with_no_intervals(self):
        serializer = ScheduleSerializer(data={"thursday": []})

        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["thursday"] == []

    def test_valid_schedule(self):
        data = {
            "monday": [
                {"start_time": time(9, 0), "end_time": time(10, 0)},
                {"start_time": time(10, 40), "end_time": time(11, 20)},
            ]
        }
        serializer = ScheduleSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_overlapping_intervals(self):
        data = {
            "tuesday": [
                {"start_time": time(9, 0), "end_time": time(10, 0)},
                {"start_time": time(9, 50), "end_time": time(11, 0)},
            ]
        }
        serializer = ScheduleSerializer(data=data)
        assert not serializer.is_valid()
        expected = "Intervals on tuesday overlap: '09:00:00–10:00:00 and 09:50:00–11:00:00'"
        assert serializer.errors["schedule"][0] == expected

    def test_gap_too_small_between_intervals(self):
        gap = MINIMUM_TIME_INTERVAL_MINUTES - 1
        data = {
            "wednesday": [
                {"start_time": time(9, 0), "end_time": time(10, 0)},
                {"start_time": time(10, gap), "end_time": time(11, 0)},
            ]
        }
        serializer = ScheduleSerializer(data=data)
        assert not serializer.is_valid()
        expected = (
            f"Intervals on wednesday must have at least {MINIMUM_TIME_INTERVAL_MINUTES} minutes between them: "
            f"'09:00:00–10:00:00 and 10:{gap:02d}:00–11:00:00'"
        )
        assert serializer.errors["schedule"][0] == expected

    def test_empty_days_are_filled_on_output(self):
        data = {
            "friday": [
                {"start_time": time(8, 0), "end_time": time(9, 0)},
            ]
        }
        serializer = ScheduleSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        output = serializer.to_representation(serializer.validated_data)
        for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
            assert day in output


@pytest.mark.django_db
class TestCreateBarrierPhoneSerializer:
    def test_valid_data_as_admin(self, admin_user, user, barrier):
        context = {"request": type("Request", (), {"user": admin_user})(), "as_admin": True, "barrier": barrier}
        data = {
            "phone": BARRIER_PERMANENT_PHONE,
            "type": BarrierPhone.PhoneType.PERMANENT,
            "name": "Test",
            "user": user.id,
        }
        serializer = CreateBarrierPhoneSerializer(data=data, context=context)
        assert serializer.is_valid(), serializer.errors

    def test_auto_assign_user_for_regular(self, user, barrier):
        context = {"request": type("Request", (), {"user": user})(), "as_admin": False, "barrier": barrier}
        data = {
            "phone": BARRIER_PERMANENT_PHONE,
            "type": BarrierPhone.PhoneType.PERMANENT,
            "name": "Test",
        }
        serializer = CreateBarrierPhoneSerializer(data=data, context=context)
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["user"] == user

    def test_missing_user_for_admin(self, admin_user, barrier):
        context = {"request": type("Request", (), {"user": admin_user})(), "as_admin": True, "barrier": barrier}
        data = {
            "phone": BARRIER_PERMANENT_PHONE,
            "type": BarrierPhone.PhoneType.PERMANENT,
            "name": "Test",
        }
        serializer = CreateBarrierPhoneSerializer(data=data, context=context)
        assert not serializer.is_valid()
        assert serializer.errors["user"][0] == "This field is required."

    def test_user_not_found_raises_not_found(self, admin_user, barrier):
        context = {"request": type("Request", (), {"user": admin_user})(), "as_admin": True, "barrier": barrier}
        data = {
            "phone": BARRIER_PERMANENT_PHONE,
            "type": BarrierPhone.PhoneType.PERMANENT,
            "name": "Test",
            "user": 99999,
        }
        serializer = CreateBarrierPhoneSerializer(data=data, context=context)
        with pytest.raises(NotFound):
            serializer.is_valid(raise_exception=True)

    @pytest.mark.parametrize(
        "as_admin,expected_author",
        [
            (True, BarrierActionLog.Author.ADMIN),
            (False, BarrierActionLog.Author.USER),
        ],
    )
    @patch("phones.serializers.BarrierPhone.create")
    def test_create_calls_model_create_and_sends_sms(
        self, mock_create, as_admin, expected_author, admin_user, user, barrier
    ):
        mock_instance = MagicMock()
        mock_log = MagicMock()
        mock_create.return_value = (mock_instance, mock_log)

        context = {"request": type("Request", (), {"user": admin_user})(), "as_admin": as_admin, "barrier": barrier}
        data = {"phone": BARRIER_PERMANENT_PHONE, "type": BarrierPhone.PhoneType.PERMANENT, "name": "Test"}
        if as_admin:
            data["user"] = user.id

        serializer = CreateBarrierPhoneSerializer(data=data, context=context)
        assert serializer.is_valid(), serializer.errors
        serializer.save()

        actual_kwargs = mock_create.call_args.kwargs
        assert actual_kwargs["user"] == (user if as_admin else admin_user)
        assert actual_kwargs["barrier"] == barrier
        assert actual_kwargs["phone"] == data["phone"]
        assert actual_kwargs["type"] == data["type"]
        assert actual_kwargs["name"] == data["name"]
        assert actual_kwargs["start_time"] is None
        assert actual_kwargs["end_time"] is None
        assert actual_kwargs["schedule"] is None
        assert actual_kwargs["author"] == expected_author
        assert actual_kwargs["reason"] == BarrierActionLog.Reason.MANUAL

        mock_instance.send_sms_to_create.assert_called_once_with(mock_log)

    def test_validation_error_other_than_not_found(self, admin_user, barrier):
        context = {"request": type("Request", (), {"user": admin_user})(), "as_admin": True, "barrier": barrier}
        data = {
            "phone": "not-a-phone",
            "type": BarrierPhone.PhoneType.PERMANENT,
            "name": "Invalid",
            "user": admin_user.id,
        }

        serializer = CreateBarrierPhoneSerializer(data=data, context=context)
        with pytest.raises(serializers.ValidationError) as exc_info:
            serializer.is_valid(raise_exception=True)

        assert "phone" in str(exc_info.value)


@pytest.mark.django_db
class TestUpdateBarrierPhoneSerializer:
    def test_valid_update_with_name_only(self, temporary_barrier_phone):
        phone, _ = temporary_barrier_phone
        serializer = UpdateBarrierPhoneSerializer(
            instance=phone,
            data={"name": "Just name"},
            partial=True,
        )
        assert serializer.is_valid(), serializer.errors

    def test_valid_update_with_time(self, temporary_barrier_phone):
        phone, _ = temporary_barrier_phone
        serializer = UpdateBarrierPhoneSerializer(
            instance=phone,
            data={
                "name": "Updated Name",
                "start_time": now() + timedelta(minutes=MINIMUM_TIME_INTERVAL_MINUTES + 1),
                "end_time": now() + timedelta(hours=10),
            },
            partial=True,
        )
        assert serializer.is_valid(), serializer.errors

    def test_partial_time_update_start_only(self, temporary_barrier_phone):
        phone, _ = temporary_barrier_phone
        serializer = UpdateBarrierPhoneSerializer(
            instance=phone,
            data={"start_time": now() + timedelta(minutes=MINIMUM_TIME_INTERVAL_MINUTES + 10)},
            partial=True,
        )
        assert not serializer.is_valid()
        assert (
            serializer.errors["time"][0]
            == "Both start_time and end_time must be provided while updating temporary phones."
        )

    def test_temporary_phone_update_too_late(self, temporary_barrier_phone):
        phone, _ = temporary_barrier_phone
        phone.start_time = now()
        phone.save()

        serializer = UpdateBarrierPhoneSerializer(
            instance=phone,
            data={
                "start_time": now() + timedelta(minutes=MINIMUM_TIME_INTERVAL_MINUTES + 1),
                "end_time": now() + timedelta(hours=10),
            },
            partial=True,
        )
        with pytest.raises(PermissionDenied) as exc:
            serializer.is_valid(raise_exception=True)
        expected = (
            f"Temporary phone number cannot be updated less than "
            f"{MINIMUM_TIME_INTERVAL_MINUTES} minutes before start."
        )
        assert exc.value.detail == expected

    @patch("phones.serializers.validate_temporary_phone")
    def test_validation_function_called_when_both_times_provided(self, mock_validate, temporary_barrier_phone):
        phone, _ = temporary_barrier_phone
        start = now() + timedelta(minutes=MINIMUM_TIME_INTERVAL_MINUTES + 1)
        end = start + timedelta(hours=1)
        serializer = UpdateBarrierPhoneSerializer(
            instance=phone,
            data={"start_time": start, "end_time": end},
            partial=True,
        )
        assert serializer.is_valid(), serializer.errors
        mock_validate.assert_called_once_with(BarrierPhone.PhoneType.TEMPORARY, start, end)

    @pytest.mark.django_db
    @patch("phones.serializers.PhoneTaskManager.edit_tasks")
    def test_update_changes_fields_on_instance(self, mock_edit_tasks, temporary_barrier_phone):
        phone, _ = temporary_barrier_phone
        new_name = "New Title"
        new_start = now() + timedelta(minutes=MINIMUM_TIME_INTERVAL_MINUTES + 5)
        new_end = new_start + timedelta(hours=1)

        serializer = UpdateBarrierPhoneSerializer(
            instance=phone,
            data={"name": new_name, "start_time": new_start, "end_time": new_end},
            partial=True,
        )
        assert serializer.is_valid(), serializer.errors
        updated_phone = serializer.save()

        assert updated_phone.name == new_name
        assert updated_phone.start_time == new_start
        assert updated_phone.end_time == new_end

    @patch("phones.serializers.PhoneTaskManager.edit_tasks")
    def test_edit_tasks_called_for_temporary_phone(self, mock_edit_tasks, temporary_barrier_phone):
        phone, _ = temporary_barrier_phone
        start = now() + timedelta(minutes=MINIMUM_TIME_INTERVAL_MINUTES + 10)
        end = start + timedelta(hours=2)

        serializer = UpdateBarrierPhoneSerializer(
            instance=phone,
            data={"start_time": start, "end_time": end},
            partial=True,
        )
        assert serializer.is_valid(), serializer.errors
        serializer.save()

        mock_edit_tasks.assert_called_once()

    @patch("phones.serializers.PhoneTaskManager.edit_tasks")
    def test_update_creates_log_entry(self, mock_edit_tasks, temporary_barrier_phone):
        phone, _ = temporary_barrier_phone

        old_name = phone.name
        old_start = phone.start_time.isoformat(timespec="minutes") if phone.start_time else None
        old_end = phone.end_time.isoformat(timespec="minutes") if phone.end_time else None

        new_name = "New Updated Name"
        new_start_dt = now() + timedelta(minutes=MINIMUM_TIME_INTERVAL_MINUTES + 10)
        new_end_dt = new_start_dt + timedelta(hours=2)

        serializer = UpdateBarrierPhoneSerializer(
            instance=phone,
            data={
                "name": new_name,
                "start_time": new_start_dt,
                "end_time": new_end_dt,
            },
            partial=True,
            context={"as_admin": True},
        )
        assert serializer.is_valid(), serializer.errors
        serializer.save()

        log = BarrierActionLog.objects.filter(
            phone=phone,
            action_type=BarrierActionLog.ActionType.UPDATE_PHONE,
        ).latest("created_at")

        assert log.author == BarrierActionLog.Author.ADMIN

        old_data = json.loads(log.old_value)
        new_data = json.loads(log.new_value)

        assert old_data["name"] == old_name
        assert old_data["type"] == "temporary"
        if old_start:
            assert old_data["start_time"] == old_start
        if old_end:
            assert old_data["end_time"] == old_end

        assert new_data["name"] == new_name
        assert new_data["type"] == "temporary"
        assert new_data["start_time"] == localtime(new_start_dt).isoformat(timespec="minutes")
        assert new_data["end_time"] == localtime(new_end_dt).isoformat(timespec="minutes")

        mock_edit_tasks.assert_called_once()


@pytest.mark.django_db
class TestUpdatePhoneScheduleSerializer:
    @patch("phones.serializers.PhoneTaskManager.edit_tasks")
    @patch("phones.serializers.ScheduleTimeInterval.replace_schedule")
    @patch("phones.serializers.validate_schedule_phone")
    def test_schedule_update_triggers_all_steps(
        self, mock_validate, mock_replace, mock_edit_tasks, schedule_barrier_phone
    ):
        phone, _ = schedule_barrier_phone
        data = {
            "monday": [{"start_time": time(9, 0), "end_time": time(10, 0)}],
            "tuesday": [{"start_time": time(11, 0), "end_time": time(12, 0)}],
        }
        serializer = UpdatePhoneScheduleSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

        result = serializer.update(phone, serializer.validated_data)

        mock_validate.assert_called_once_with(phone.type, serializer.validated_data, phone.barrier)
        mock_replace.assert_called_once_with(phone, serializer.validated_data)
        mock_edit_tasks.assert_called_once()
        assert result == phone

    @patch("phones.serializers.PhoneTaskManager.edit_tasks")
    def test_log_entry_contains_expected_data(self, mock_edit_tasks, schedule_barrier_phone):
        phone, _ = schedule_barrier_phone
        data = {
            "monday": [{"start_time": time(9, 0), "end_time": time(10, 0)}],
            "tuesday": [{"start_time": time(11, 0), "end_time": time(12, 0)}],
        }

        serializer = UpdatePhoneScheduleSerializer(data=data, context={"as_admin": True})
        assert serializer.is_valid(), serializer.errors

        serializer.update(phone, serializer.validated_data)

        log = BarrierActionLog.objects.filter(
            phone=phone,
            action_type=BarrierActionLog.ActionType.UPDATE_PHONE,
            reason=BarrierActionLog.Reason.SCHEDULE_UPDATE,
        ).latest("created_at")

        assert log.author == BarrierActionLog.Author.ADMIN
        assert log.barrier == phone.barrier

        old_data = json.loads(log.old_value)
        new_data = json.loads(log.new_value)

        assert old_data["name"] == phone.name
        assert old_data["type"] == "schedule"
        assert isinstance(old_data.get("schedule"), dict)

        assert new_data["schedule"]["monday"][0]["start_time"] == "09:00"
        assert new_data["schedule"]["tuesday"][0]["end_time"] == "12:00"
