import logging
from datetime import date, datetime, timedelta

from django.utils.timezone import now
from rest_framework import serializers
from rest_framework.exceptions import NotFound, PermissionDenied

from action_history.models import BarrierActionLog
from phones.constants import MINIMUM_TIME_INTERVAL_MINUTES
from phones.models import BarrierPhone, ScheduleTimeInterval
from phones.validators import validate_schedule_phone, validate_temporary_phone
from scheduler.task_manager import PhoneTaskManager
from users.models import User

logger = logging.getLogger(__name__)


class BarrierPhoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = BarrierPhone
        exclude = ["device_serial_number"]


class ScheduleTimeIntervalSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduleTimeInterval
        fields = ["start_time", "end_time"]

    def validate(self, attrs):
        start = attrs["start_time"]
        end = attrs["end_time"]

        if start >= end:
            raise serializers.ValidationError({"time": "end_time must be after start_time."})

        duration = datetime.combine(date.today(), end) - datetime.combine(date.today(), start)
        if duration < timedelta(minutes=MINIMUM_TIME_INTERVAL_MINUTES):
            message = f"Interval must be at least {MINIMUM_TIME_INTERVAL_MINUTES} minutes long."
            raise serializers.ValidationError({"time": message})

        return attrs


class ScheduleSerializer(serializers.Serializer):
    monday = ScheduleTimeIntervalSerializer(many=True, required=False)
    tuesday = ScheduleTimeIntervalSerializer(many=True, required=False)
    wednesday = ScheduleTimeIntervalSerializer(many=True, required=False)
    thursday = ScheduleTimeIntervalSerializer(many=True, required=False)
    friday = ScheduleTimeIntervalSerializer(many=True, required=False)
    saturday = ScheduleTimeIntervalSerializer(many=True, required=False)
    sunday = ScheduleTimeIntervalSerializer(many=True, required=False)

    @staticmethod
    def validate_intervals(day, intervals):
        if not intervals:
            return

        sorted_intervals = sorted(intervals, key=lambda i: i["start_time"])
        for i in range(1, len(sorted_intervals)):
            prev = sorted_intervals[i - 1]
            curr = sorted_intervals[i]
            if curr["start_time"] <= prev["end_time"]:
                message = (
                    f"Intervals on {day} overlap: "
                    f"'{prev['start_time']}–{prev['end_time']} and {curr['start_time']}–{curr['end_time']}'"
                )
                raise serializers.ValidationError({"schedule": message})

            prev_end = datetime.combine(date.today(), prev["end_time"])
            curr_start = datetime.combine(date.today(), curr["start_time"])
            gap = curr_start - prev_end
            if gap < timedelta(minutes=MINIMUM_TIME_INTERVAL_MINUTES):
                message = (
                    f"Intervals on {day} must have at least {MINIMUM_TIME_INTERVAL_MINUTES} minutes between them: "
                    f"'{prev['start_time']}–{prev['end_time']} and {curr['start_time']}–{curr['end_time']}'"
                )
                raise serializers.ValidationError({"schedule": message})

    def validate(self, attrs):
        for day, intervals in attrs.items():
            self.validate_intervals(day, intervals)
        return attrs

    def to_representation(self, instance):
        result = super().to_representation(instance)

        for day in ScheduleTimeInterval.DayOfWeek.values:
            result.setdefault(day, [])

        return result


class CreateBarrierPhoneSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True),
        required=False,
        write_only=True,
        help_text="User for whom the phone is being created (required for admins).",
    )

    schedule = ScheduleSerializer(required=False, write_only=True)

    class Meta:
        model = BarrierPhone
        fields = ["phone", "type", "name", "start_time", "end_time", "user", "schedule"]

    def to_internal_value(self, data):
        try:
            return super().to_internal_value(data)
        except serializers.ValidationError as exc:
            errors = exc.detail
            for field, messages in errors.items():
                if any("does not exist" in str(msg) for msg in messages):
                    raise NotFound(f"{field.capitalize()} not found.")
            raise

    def validate(self, attrs):
        request = self.context["request"]
        as_admin = self.context.get("as_admin", False)
        barrier = self.context.get("barrier")

        attrs["barrier"] = barrier

        if as_admin:
            if not attrs.get("user"):
                raise serializers.ValidationError({"user": "This field is required."})
        else:
            attrs["user"] = request.user

        return attrs

    def create(self, validated_data):
        as_admin = self.context.get("as_admin", False)

        schedule_data = validated_data.pop("schedule", None)
        phone, log = BarrierPhone.create(
            user=validated_data["user"],
            barrier=validated_data["barrier"],
            phone=validated_data["phone"],
            type=validated_data["type"],
            name=validated_data.get("name", ""),
            author=BarrierActionLog.Author.ADMIN if as_admin else BarrierActionLog.Author.USER,
            reason=BarrierActionLog.Reason.MANUAL,
            start_time=validated_data.get("start_time"),
            end_time=validated_data.get("end_time"),
            schedule=schedule_data,
        )
        phone.send_sms_to_create(log)
        return phone


class UpdateBarrierPhoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = BarrierPhone
        fields = ["name", "start_time", "end_time"]

    def validate(self, attrs):
        phone = self.instance
        start_time = attrs.get("start_time")
        end_time = attrs.get("end_time")

        if phone.type == BarrierPhone.PhoneType.TEMPORARY:
            # If one time field is passed, both must be
            if (start_time is not None) ^ (end_time is not None):
                raise serializers.ValidationError(
                    {"time": "Both start_time and end_time must be provided while updating temporary phones."}
                )

            # Only validate times if provided
            if start_time and end_time:
                if phone.start_time and phone.start_time < now() + timedelta(minutes=MINIMUM_TIME_INTERVAL_MINUTES):
                    message = (
                        f"Temporary phone number cannot be updated less than "
                        f"{MINIMUM_TIME_INTERVAL_MINUTES} minutes before start."
                    )
                    raise PermissionDenied(message)
                validate_temporary_phone(phone.type, start_time, end_time)

        return attrs

    def update(self, phone: BarrierPhone, validated_data):
        as_admin = self.context.get("as_admin", False)
        old_value = phone.describe_phone_params()

        for attr, value in validated_data.items():
            setattr(phone, attr, value)
        phone.save()

        new_value = phone.describe_phone_params()

        log = BarrierActionLog.objects.create(
            phone=phone,
            barrier=phone.barrier,
            author=BarrierActionLog.Author.ADMIN if as_admin else BarrierActionLog.Author.USER,
            action_type=BarrierActionLog.ActionType.UPDATE_PHONE,
            old_value=old_value,
            new_value=new_value,
        )

        if phone.type == BarrierPhone.PhoneType.TEMPORARY:
            PhoneTaskManager(phone, log).edit_tasks()

        return phone


class UpdatePhoneScheduleSerializer(ScheduleSerializer):
    """Partial update of schedule: only update the days that were explicitly passed."""

    def update(self, phone: BarrierPhone, validated_data):
        as_admin = self.context.get("as_admin", False)
        old_value = phone.describe_phone_params()

        validate_schedule_phone(phone.type, validated_data, phone.barrier)
        ScheduleTimeInterval.replace_schedule(phone, validated_data)

        new_value = phone.describe_phone_params()
        log = BarrierActionLog.objects.create(
            phone=phone,
            barrier=phone.barrier,
            author=BarrierActionLog.Author.ADMIN if as_admin else BarrierActionLog.Author.USER,
            action_type=BarrierActionLog.ActionType.UPDATE_PHONE,
            reason=BarrierActionLog.Reason.SCHEDULE_UPDATE,
            old_value=old_value,
            new_value=new_value,
        )

        PhoneTaskManager(phone, log).edit_tasks()

        return phone
