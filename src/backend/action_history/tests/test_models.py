import pytest
from django.core.exceptions import PermissionDenied

from action_history.models import BarrierActionLog


@pytest.mark.django_db
class TestBarrierActionLog:
    def test_create_log_entry(self, barrier, barrier_phone):
        phone, _ = barrier_phone
        log = BarrierActionLog.objects.create(
            phone=phone,
            barrier=barrier,
            author=BarrierActionLog.Author.ADMIN,
            action_type=BarrierActionLog.ActionType.UPDATE_PHONE,
            reason=BarrierActionLog.Reason.MANUAL,
            old_value=None,
            new_value="Updated phone",
        )
        assert log.id is not None
        assert log.phone == phone
        assert log.barrier == barrier
        assert log.author == BarrierActionLog.Author.ADMIN
        assert log.action_type == BarrierActionLog.ActionType.UPDATE_PHONE
        assert log.reason == BarrierActionLog.Reason.MANUAL
        assert log.old_value is None
        assert log.new_value == "Updated phone"
        assert log.created_at is not None

    def test_str_representation(self, barrier, barrier_phone):
        phone, _ = barrier_phone
        log = BarrierActionLog.objects.create(
            phone=phone,
            barrier=barrier,
            author=BarrierActionLog.Author.USER,
            action_type=BarrierActionLog.ActionType.DELETE_PHONE,
            reason=BarrierActionLog.Reason.USER_DELETED,
        )
        expected = f"'{log.id}' [{log.created_at:%Y-%m-%d %H:%M}] by user delete_phone (user_deleted) for {phone}"
        assert str(log) == expected

    def test_delete_raises_error(self, barrier, barrier_phone):
        phone, _ = barrier_phone
        log = BarrierActionLog.objects.create(
            phone=phone,
            barrier=barrier,
            author=BarrierActionLog.Author.SYSTEM,
            action_type=BarrierActionLog.ActionType.BARRIER_SETTING,
            reason=BarrierActionLog.Reason.BARRIER_DELETED,
        )
        log_id = log.id
        with pytest.raises(PermissionDenied):
            log.delete()

        assert BarrierActionLog.objects.filter(id=log_id).exists()
