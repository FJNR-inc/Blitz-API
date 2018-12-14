from datetime import datetime

import pytz
from django.conf import settings
from rest_framework.test import APITestCase

from blitz_api.factories import UserFactory

from ..models import Retirement, WaitQueueNotification

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


class WaitQueueNotificationTests(APITestCase):
    @classmethod
    def setUpClass(cls):
        super(WaitQueueNotificationTests, cls).setUpClass()
        cls.user = UserFactory()
        cls.retirement = Retirement.objects.create(
            name="random_retirement",
            details="This is a description of the retirement.",
            seats=40,
            address_line1="123 random street",
            postal_code="123 456",
            state_province="Random state",
            country="Random country",
            price=3,
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 17, 12)),
            min_day_refund=7,
            min_day_exchange=7,
            refund_rate=100,
            is_active=True,
        )

    def test_create(self):
        """
        Ensure that we can create a retirement.
        """
        wait_queue = WaitQueueNotification.objects.create(
            user=self.user,
            retirement=self.retirement,
        )

        self.assertEqual(
            wait_queue.__str__(),
            ', '.join(["random_retirement", str(self.user)])
        )
