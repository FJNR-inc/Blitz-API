import json
from datetime import datetime
from unittest import mock

import responses
from django.test import TestCase
from django.utils import timezone

from cron_manager.models import Task
from log_management.models import Log


class CronManagerTests(TestCase):

    def setUp(self) -> None:

        self.url_test = 'http://local/retreat/wait_queue_places/15/notify'

        self.task = Task.objects.create(
            url=self.url_test,
            description='test_description_task',
            execution_datetime=timezone.now(),
            execution_interval=86400000
        )

        self.task_without_interval = Task.objects.create(
            url=self.url_test,
            description='test_description_task',
            execution_datetime=timezone.now(),
        )

    def test_can_execute_after(self):
        date_after_execution_datetime = \
            self.task.execution_datetime + timezone.timedelta(
                minutes=10)
        with mock.patch(
                'django.utils.timezone.now',
                return_value=date_after_execution_datetime):
            self.assertTrue(self.task.can_be_execute)

    def test_can_execute_before(self):
        date_before_execution_datetime = \
            self.task.execution_datetime - timezone.timedelta(
                minutes=10
            )
        with mock.patch(
                'django.utils.timezone.now',
                return_value=date_before_execution_datetime):
            self.assertFalse(self.task.can_be_execute)

    def test_can_execute_after_without_execution_interval(self):
        date_after_execution_datetime = \
            self.task_without_interval.execution_datetime + \
            timezone.timedelta(
                minutes=10)
        with mock.patch(
                'django.utils.timezone.now',
                return_value=date_after_execution_datetime):

            self.assertTrue(
                self.task_without_interval.can_be_execute)

    @responses.activate
    def test_execution(self):
        responses.add(
            responses.GET,
            self.url_test,
            json={
                'stop': False
            },
            status=200
        )
        date_after_execution_datetime = \
            self.task.execution_datetime + timezone.timedelta(
                minutes=10)
        with mock.patch(
                'django.utils.timezone.now',
                return_value=date_after_execution_datetime):
            self.task.execute()

            self.assertEqual(
                self.task.executions.count(),
                1
            )

            self.assertTrue(self.task.active)

    @responses.activate
    def test_execution_one_time(self):
        responses.add(
            responses.GET,
            self.url_test,
            json={
                'stop': False
            },
            status=200
        )
        date_after_execution_datetime = \
            self.task_without_interval.execution_datetime\
            + timezone.timedelta(
                minutes=10)
        with mock.patch(
                'django.utils.timezone.now',
                return_value=date_after_execution_datetime):
            self.task_without_interval.execute()

            self.assertEqual(
                self.task_without_interval.executions.count(),
                1
            )

            self.assertFalse(self.task_without_interval.active)
            self.assertFalse(
                self.task_without_interval.can_be_execute)

    @responses.activate
    def test_execution_one_time_failed(self):
        responses.add(
            responses.GET,
            self.url_test,
            json={
                'stop': False
            },
            status=300
        )
        date_after_execution_datetime = \
            self.task_without_interval.execution_datetime\
            + timezone.timedelta(
                minutes=10)
        with mock.patch(
                'django.utils.timezone.now',
                return_value=date_after_execution_datetime):
            self.task_without_interval.execute()

            self.assertEqual(
                self.task_without_interval.executions.count(),
                1
            )

            self.assertTrue(self.task_without_interval.active)
            self.assertTrue(
                self.task_without_interval.can_be_execute)

            execution = self.task_without_interval.executions.first()
            self.assertFalse(execution.success)

    @responses.activate
    def test_execution_fail(self):
        responses.add(
            responses.GET,
            self.url_test,
            status=300
        )
        date_after_execution_datetime = \
            self.task.execution_datetime\
            + timezone.timedelta(
                minutes=10)
        with mock.patch(
                'django.utils.timezone.now',
                return_value=date_after_execution_datetime):
            self.task.execute()

            self.assertEqual(
                self.task.executions.count(),
                1
            )

            self.assertTrue(self.task.active)

            execution = self.task.executions.first()
            self.assertFalse(execution.success)
