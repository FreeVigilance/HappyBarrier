import logging

from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore

_scheduler = None
logger = logging.getLogger(__name__)


def get_scheduler(paused: bool = True, force_new: bool = False):
    global _scheduler

    if _scheduler is None or force_new:
        logger.info(f"Creating {'new' if force_new else 'default'} scheduler instance. Paused: {paused}")
        _scheduler = BackgroundScheduler()
        _scheduler.add_jobstore(DjangoJobStore(), alias="default")

        logger.info(f"Starting scheduler instance. Paused: {paused}")
        _scheduler.start(paused=paused)

    elif not _scheduler.running:
        logger.info(f"Starting existing scheduler. Paused: {paused}")
        _scheduler.start(paused=paused)

    return _scheduler
