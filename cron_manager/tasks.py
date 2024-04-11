from celery import shared_task
from django.conf import settings
import requests


@shared_task
def trigger_task_executions():
    from .cron_function import execute_tasks

    execute_tasks()

    try:
        status_url = settings.LOCAL_SETTINGS['STATUS_URLS']['TASK_EXECUTION']

        if status_url:
            requests.get(status_url)
    except Exception:
        # We don't want to block the task because of a status update
        # Status system should already report the error if needed
        pass
