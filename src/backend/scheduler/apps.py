import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class SchedulerConfig(AppConfig):
    name = "scheduler"

    def ready(self):
        logger.info("Scheduler starting...")
        from scheduler.scheduler import get_scheduler

        get_scheduler()
