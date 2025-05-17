from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore

from scheduler.scheduler import get_scheduler


def test_get_scheduler_initialization():
    scheduler = get_scheduler()
    assert isinstance(scheduler, BackgroundScheduler)
    assert "default" in scheduler._jobstores
    assert isinstance(scheduler._jobstores["default"], DjangoJobStore)
    assert scheduler.running
