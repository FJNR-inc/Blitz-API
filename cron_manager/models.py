import datetime

import requests
from django.db import models
from django.utils import timezone

from django.utils.translation import gettext_lazy as _


class Task(models.Model):
    """Model for tasks"""

    url = models.URLField(
        verbose_name=_("URL to execute"),
    )

    description = models.CharField(
        max_length=150,
        verbose_name=_("Description"),
    )

    execution_datetime = models.DateTimeField(
        verbose_name=_("Execution datetime"),
    )

    execution_interval = models.BigIntegerField(
        blank=True,
        null=True,
        verbose_name=_("Execution intervals ms"),
    )

    active = models.BooleanField(
        default=True,
        verbose_name=_("Active"),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created_at"),
    )

    def __str__(self):
        return self.description

    @property
    def last_execution(self):
        return self.executions.filter(success=True)\
            .order_by('-executed_at').first()

    def next_execution_datetime(self):
        if self.last_execution:
            if self.execution_interval:
                next_execution_datetime = \
                    self.last_execution.executed_at + \
                    datetime.timedelta(milliseconds=self.execution_interval)
            else:
                next_execution_datetime = False
        else:
            next_execution_datetime = self.execution_datetime
        return next_execution_datetime

    @property
    def can_be_execute(self):

        if self.active:
            next_execution_datetime = self.next_execution_datetime()

            if next_execution_datetime:
                return timezone.now() >= self.next_execution_datetime()
            else:
                return False
        else:
            return False

    def execute(self):

        executed_at = self.next_execution_datetime()

        execution = Execution.objects.create(
            task=self,
            executed_at=executed_at
        )

        response = requests.get(self.url)

        success = False
        if 200 <= response.status_code < 300:
            success = True
            try:
                content = response.json()
                stop_cron_task = content.get('stop', False)
                if stop_cron_task or not self.execution_interval:
                    self.active = False
                    self.save()
            except Exception:
                success = False
        execution.success = success
        execution.http_code = response.status_code
        execution.http_response = response.text
        execution.save()


class Execution(models.Model):
    """Model to log execution of tasks"""

    task = models.ForeignKey(
        'Task',
        related_name='executions',
        on_delete=models.CASCADE,
        verbose_name="Task"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created at"),
    )

    executed_at = models.DateTimeField(
        verbose_name=_("Executed at"),
    )

    success = models.BooleanField(
        default=False,
        blank=True,
        null=True,
        verbose_name=_("Succeded ?"),
    )

    http_code = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_("HTTP code"),
    )

    http_response = models.TextField(
        verbose_name=_("HTTP response"),
        blank=True,
        null=True,
    )

    def __str__(self):
        return f'{self.task} - {self.success}'
