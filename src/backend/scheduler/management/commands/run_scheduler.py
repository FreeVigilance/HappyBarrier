import logging
import signal
import time

from django.core.management.base import BaseCommand

from scheduler.scheduler import get_scheduler

logger = logging.getLogger(__name__)
stop_signal_received = False


def signal_handler(signum, frame):
    global stop_signal_received
    logger.info("Received shutdown signal")
    stop_signal_received = True


class Command(BaseCommand):
    help = "Starting APScheduler and keeps it active."

    def handle(self, *args, **options):
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        logger.info("Starting APScheduler...")
        scheduler = get_scheduler(paused=False, force_new=True)

        try:
            while not stop_signal_received:
                time.sleep(1)
                scheduler.wakeup()
        except KeyboardInterrupt:
            logger.info("Scheduler interrupted")
        finally:
            logger.info("Shutting down scheduler...")
            scheduler.shutdown(wait=True)
            logger.info("Scheduler stopped")
