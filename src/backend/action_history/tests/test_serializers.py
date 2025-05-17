import pytest
from rest_framework.exceptions import ValidationError

from action_history.models import BarrierActionLog
from action_history.serializers import BarrierActionLogSerializer


@pytest.mark.django_db
class TestBarrierActionLogSerializer:
    def test_serializes_log_correctly(self, barrier, barrier_phone):
        phone, _ = barrier_phone
        log = BarrierActionLog.objects.create(
            phone=phone,
            barrier=barrier,
            author=BarrierActionLog.Author.ADMIN,
            action_type=BarrierActionLog.ActionType.UPDATE_PHONE,
            reason=BarrierActionLog.Reason.MANUAL,
            old_value="old",
            new_value="new",
        )

        serializer = BarrierActionLogSerializer(instance=log)
        data = serializer.data

        assert data["id"] == log.id
        assert data["phone"] == log.phone.id
        assert data["barrier"] == log.barrier.id
        assert data["author"] == log.author
        assert data["action_type"] == log.action_type
        assert data["reason"] == log.reason
        assert data["old_value"] == "old"
        assert data["new_value"] == "new"
        assert "created_at" in data

    def test_validation_fails_on_missing_required_fields(self):
        serializer = BarrierActionLogSerializer(data={})
        with pytest.raises(ValidationError):
            serializer.is_valid(raise_exception=True)
