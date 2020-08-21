from datetime import datetime

import pytz
from django.conf import settings
from rest_framework.test import APITestCase

from blitz_api.factories import UserFactory

from ..models import Retreat, WaitQueue, RetreatType, RetreatDate

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


class WaitQueueTests(APITestCase):
    @classmethod
    def setUpClass(cls):
        super(WaitQueueTests, cls).setUpClass()
        cls.user = UserFactory()
        cls.retreatType = RetreatType.objects.create(
            name="Type 1",
            minutes_before_display_link=10,
            number_of_tomatoes=4,
        )
        cls.retreat = Retreat.objects.create(
            name="mega_retreat",
            details="This is a description of the mega retreat.",
            seats=400,
            address_line1="123 random street",
            postal_code="123 456",
            state_province="Random state",
            country="Random country",
            price=199,
            min_day_refund=7,
            min_day_exchange=7,
            refund_rate=50,
            accessibility=True,
            form_url="example.com",
            carpool_url='example2.com',
            review_url='example3.com',
            has_shared_rooms=True,
            toilet_gendered=False,
            room_type=Retreat.SINGLE_OCCUPATION,
            type=cls.retreatType,
        )
        RetreatDate.objects.create(
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 17, 12)),
            retreat=cls.retreat,
        )
        cls.retreat.activate()

    def test_create(self):
        """
        Ensure that we can create a retreat.
        """
        wait_queue = WaitQueue.objects.create(
            user=self.user,
            retreat=self.retreat,
        )

        self.assertEqual(
            wait_queue.__str__(),
            ', '.join(["mega_retreat", str(self.user)])
        )
