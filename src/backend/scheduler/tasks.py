import logging

from action_history.models import BarrierActionLog
from message_management.services import SMSService
from phones.models import BarrierPhone

logger = logging.getLogger(__name__)


def send_open_sms(phone: BarrierPhone, log: BarrierActionLog):
    logger.info(f"Sending scheduled OPEN SMS for phone {phone.id} in barrier {phone.barrier.id}")
    SMSService.send_add_phone_command(phone, log)


def send_close_sms(phone: BarrierPhone, log: BarrierActionLog):
    logger.info(f"Sending scheduled CLOSE SMS for phone {phone.id} in barrier {phone.barrier.id}")
    SMSService.send_delete_phone_command(phone, log)


def send_delete_phone(phone: BarrierPhone, *args):
    logger.info(f"Auto-deleting temporary phone {phone.id}")
    phone.remove(author=BarrierActionLog.Author.SYSTEM, reason=BarrierActionLog.Reason.END_OF_TIME)
