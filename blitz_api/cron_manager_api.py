from django.utils import timezone

from django.urls import reverse

from blitz_api import settings
from cron_manager.models import Task


class CronManager:

    def __init__(self):
        self.url_to_call = settings.EXTERNAL_SCHEDULER['URL_TO_CALL']

    def create_task(self, data):
        Task.objects.create(**data)

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

