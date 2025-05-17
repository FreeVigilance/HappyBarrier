from unittest.mock import patch

import pytest

from action_history.models import BarrierActionLog
from scheduler.tasks import send_close_sms, send_delete_phone, send_open_sms


@pytest.mark.django_db
@patch("scheduler.tasks.SMSService.send_add_phone_command")
def test_send_open_sms_calls_add_command(mock_send_add, barrier_phone):
    phone, log = barrier_phone
    send_open_sms(phone, log)

    mock_send_add.assert_called_once_with(phone, log)


@pytest.mark.django_db
@patch("scheduler.tasks.SMSService.send_delete_phone_command")
def test_send_close_sms_calls_delete_command(mock_send_delete, barrier_phone):
    phone, log = barrier_phone
    send_close_sms(phone, log)

    mock_send_delete.assert_called_once_with(phone, log)


@pytest.mark.django_db
@patch("phones.models.BarrierPhone.remove")
def test_send_delete_phone_calls_remove(mock_remove, barrier_phone):
    phone, log = barrier_phone
    send_delete_phone(phone, log)

    mock_remove.assert_called_once_with(
        author=BarrierActionLog.Author.SYSTEM, reason=BarrierActionLog.Reason.END_OF_TIME
    )
