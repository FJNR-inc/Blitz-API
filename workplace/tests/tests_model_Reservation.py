import pytz

from datetime import timedelta, datetime

from rest_framework.test import APITestCase

from django.conf import settings
from django.utils import timezone

from blitz_api.factories import UserFactory

from ..models import Period, TimeSlot, Reservation

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


class ReservationTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(ReservationTests, cls).setUpClass()
        cls.user = UserFactory()
        cls.period = Period.objects.create(
            name="random_period",
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(weeks=4),
            price=3,
            is_active=True,
        )
        cls.timeslot = TimeSlot.objects.create(
            name="evening_time_slot",
            period=cls.period,
            price=3,
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 12)),
        )

    def test_create(self):
        """
        Ensure that we can create a time_slot.
        """
        reservation = Reservation.objects.create(
            user=self.user,
            timeslot=self.timeslot,
            is_active=True,
        )

        self.assertEqual(str(reservation), str(self.user))
