import pytest

from barriers.models import BarrierLimit, UserBarrier
from barriers.serializers import BarrierLimitSerializer, BarrierSerializer
from users.models import User


@pytest.mark.django_db
class TestBarrierSerializer:
    def test_owner_phone_hidden_for_private(self, user, barrier):
        barrier.owner.phone_privacy = User.PhonePrivacy.PRIVATE
        barrier.owner.save()

        request = type("Request", (), {"user": user})()
        serializer = BarrierSerializer(barrier, context={"request": request})

        assert serializer.data["owner"]["phone"] is None

    def test_owner_phone_visible_for_public(self, user, barrier):
        barrier.owner.phone_privacy = User.PhonePrivacy.PUBLIC
        barrier.owner.save()

        request = type("Request", (), {"user": user})()
        serializer = BarrierSerializer(barrier, context={"request": request})

        assert serializer.data["owner"]["phone"] == barrier.owner.phone

    def test_owner_phone_visible_for_protected_with_access(self, user, barrier, access_request):
        barrier.owner.phone_privacy = User.PhonePrivacy.PROTECTED
        barrier.owner.save()

        UserBarrier.create(user, barrier, access_request)

        request = type("Request", (), {"user": user})()
        serializer = BarrierSerializer(barrier, context={"request": request})

        assert serializer.data["owner"]["phone"] == barrier.owner.phone

    def test_device_phone_hidden_without_access(self, user, barrier):
        request = type("Request", (), {"user": user})()
        serializer = BarrierSerializer(barrier, context={"request": request})

        assert serializer.data["device_phone"] is None

    def test_device_phone_visible_with_access(self, user, barrier, access_request):
        UserBarrier.create(user, barrier, access_request)

        request = type("Request", (), {"user": user})()
        serializer = BarrierSerializer(barrier, context={"request": request})

        assert serializer.data["device_phone"] == barrier.device_phone


@pytest.mark.django_db
class TestBarrierLimitSerializer:
    def test_serializes_all_fields_except_timestamps(self, barrier):
        limits = BarrierLimit.objects.create(
            barrier=barrier,
            user_phone_limit=3,
            user_temp_phone_limit=1,
            global_temp_phone_limit=5,
            sms_weekly_limit=50,
        )

        serialized = BarrierLimitSerializer(limits).data

        assert serialized["user_phone_limit"] == 3
        assert serialized["user_temp_phone_limit"] == 1
        assert serialized["global_temp_phone_limit"] == 5
        assert serialized["sms_weekly_limit"] == 50
        assert "created_at" not in serialized
        assert "updated_at" not in serialized

    def test_serializes_null_values(self, barrier):
        limits = BarrierLimit.objects.create(barrier=barrier)

        serialized = BarrierLimitSerializer(limits).data

        assert serialized["user_phone_limit"] is None
        assert serialized["user_temp_phone_limit"] is None
        assert serialized["global_temp_phone_limit"] is None
        assert serialized["sms_weekly_limit"] is None
