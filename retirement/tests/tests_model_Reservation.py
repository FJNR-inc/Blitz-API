from datetime import datetime, timedelta

import pytz
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from rest_framework.test import APITestCase

from blitz_api.factories import UserFactory

from store.models import Order, OrderLine

from ..models import Reservation, Retirement

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


class ReservationTests(APITestCase):
    @classmethod
    def setUpClass(cls):
        super(ReservationTests, cls).setUpClass()
        cls.user = UserFactory()
        cls.retirement_type = ContentType.objects.get_for_model(Retirement)
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
            accessibility=True,
            form_url="example.com",
            carpool_url='example2.com',
            review_url='example3.com',
        )
        cls.order = Order.objects.create(
            user=cls.user,
            transaction_date=timezone.now(),
            authorization_id=1,
            settlement_id=1,
        )
        cls.order_line = OrderLine.objects.create(
            order=cls.order,
            quantity=999,
            content_type=cls.retirement_type,
            object_id=1,
        )

    def test_create(self):
        """
        Ensure that we can create a time_slot.
        """
        reservation = Reservation.objects.create(
            user=self.user,
            retirement=self.retirement,
            order_line=self.order_line,
            is_active=True,
        )

        self.assertEqual(str(reservation), str(self.user))
