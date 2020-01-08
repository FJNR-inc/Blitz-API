from cron_manager.models import Task


def execute_tasks():

    task_actives = Task.objects.filter(
        active=True
    )

    for task in task_actives:
        if task.can_be_execute:
            task.execute()
