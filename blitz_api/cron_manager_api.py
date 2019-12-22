import json
import traceback
from django.utils import timezone

import requests
from django.core.mail import mail_admins
from django.urls import reverse

from blitz_api import settings


class CronManager:

    url: str = None
    token: str = None
    task_path = '/tasks'

    def __init__(self):
        self.url = settings.EXTERNAL_SCHEDULER['URL']
        self.url_to_call = settings.EXTERNAL_SCHEDULER['URL_TO_CALL']
        self.login()

    def login(self):
        try:
            auth_data = {
                "username": settings.EXTERNAL_SCHEDULER['USER'],
                "password": settings.EXTERNAL_SCHEDULER['PASSWORD']
            }
            auth = requests.post(
                self.url + "/authentication",
                json=auth_data,
            )
            auth.raise_for_status()

            self.token = json.loads(auth.content)['token']
        except (requests.exceptions.HTTPError,
                requests.exceptions.ConnectionError) as err:
            mail_admins(
                "Thèsez-vous: external scheduler error",
                traceback.format_exc()
            )

    def create_task(self, data):

        try:
            r = requests.post(
                self.url + self.task_path,
                json=data,
                headers={
                    'Authorization':
                        f'Token {self.token}'
                },
                timeout=(10, 10),
            )
            r.raise_for_status()
        except (requests.exceptions.HTTPError,
                requests.exceptions.ConnectionError) as err:
            mail_admins(
                "Thèsez-vous: external scheduler error",
                traceback.format_exc()
            )

    def create_wait_queue_place_notification(self, wait_queue_place_id):
        wait_queue_place_url = self.url_to_call + reverse(
                'retreat:waitqueueplace-notify',
                args=[wait_queue_place_id]
            )

        data = {
            "hour": timezone.now().hour,
            "minute": (timezone.now().minute + 5) % 60,
            "url": wait_queue_place_url,
            "description": "Retreat wait queue notification"
        }

        self.create_task(data)
