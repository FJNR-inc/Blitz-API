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

    def get_retreat_target_url(self, retreat, email):
        """
        :param retreat: The Retreat associate with this email
        :param email: The AutomaticEmail we want to schedule
        :return: url for the task
        """
        return self.url_to_call + reverse(
            'retreat:retreat-detail',
            args=[retreat.id]
        ) + "/execute_automatic_email/?email=" + str(email.id)

    def create_email_task(self, retreat, email, execution_date):
        """

        :param retreat: The Retreat associate with this email
        :param email: The AutomaticEmail we want to schedule
        :return: None
        """
        target_url = self.get_retreat_target_url(retreat, email)

        description = "Automatic email #" + str(email.id) + \
                      " for retreat #" + str(retreat.id)
        data = {
            "execution_datetime": execution_date,
            "url": target_url,
            "description": description
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
            "description": "Retreat reminder notification"
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
