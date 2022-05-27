from celery import shared_task


@shared_task
def trigger_task_executions():
    from .cron_function import execute_tasks

    execute_tasks()
