import json
import traceback
from django.utils import timezone

import requests
from django.core.mail import mail_admins
from django.urls import reverse

from blitz_api import settings
from cron_manager.models import Task


class CronManager:

    def __init__(self):
        self.url_to_call = settings.EXTERNAL_SCHEDULER['URL_TO_CALL']

    def create_task(self, data):
        Task.objects.create(**data)

    def create_wait_queue_place_notification(self, wait_queue_place_id):
        wait_queue_place_url = self.url_to_call + reverse(
                'retreat:waitqueueplace-notify',
                args=[wait_queue_place_id]
            )

        data = {
            "execution_datetime": timezone.now(),
            "execution_interval": 1000 * 60 * 60 * 24,
            "url": wait_queue_place_url,
            "description": "Retreat wait queue notification"
        }

        self.create_task(data)

    def create_remind_user(self, retreat_id, reminder_date):
        remind_users_url = self.url_to_call + reverse(
            'retreat:retreat-detail',
            args=[retreat_id]
        ) + "/remind_users"
        data = {
            "execution_datetime": reminder_date,
            "url": remind_users_url,
            "description": "Retreat 7-days reminder notification"
        }

        self.create_task(data)

    def create_recap(self, retreat_id, throwback_date):
        remind_users_url = self.url_to_call + reverse(
            'retreat:retreat-detail',
            args=[retreat_id]
        ) + "/recap"
        data = {
            "execution_datetime": throwback_date,
            "url": remind_users_url,
            "description": "Retreat post-event notification"
        }

        self.create_task(data)
