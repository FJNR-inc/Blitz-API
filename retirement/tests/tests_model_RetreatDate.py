from datetime import datetime

from django.contrib.contenttypes.models import ContentType

import pytz
from django.conf import settings
from rest_framework.test import APITestCase

from retirement.models import (
    Retreat,
    RetreatDate,
    RetreatType,
)

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


class RetreatDateTests(APITestCase):

    def setUp(self):
        self.retreat_type = ContentType.objects.get_for_model(Retreat)
        self.retreatType = RetreatType.objects.create(
            name="Type 1",
            minutes_before_display_link=10,
            number_of_tomatoes=4,
        )
        self.retreat = Retreat.objects.create(
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
            display_start_time=LOCAL_TIMEZONE.localize(
                datetime(2130, 1, 15, 8)
            ),
            type=self.retreatType,
            number_of_tomatoes=37,
        )

    def test_property_is_last_date(self):
        one = RetreatDate.objects.create(
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 17, 12)),
            retreat=self.retreat,
        )
        two = RetreatDate.objects.create(
            start_time=LOCAL_TIMEZONE.localize(datetime(2140, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2140, 1, 17, 12)),
            retreat=self.retreat,
        )
        three = RetreatDate.objects.create(
            start_time=LOCAL_TIMEZONE.localize(datetime(2150, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2150, 1, 17, 12)),
            retreat=self.retreat,
        )

        self.assertEqual(False, one.is_last_date)
        self.assertEqual(False, two.is_last_date)
        self.assertEqual(True, three.is_last_date)

    def test_property_number_of_tomatoes(self):
        one = RetreatDate.objects.create(
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 17, 12)),
            retreat=self.retreat,
        )
        two = RetreatDate.objects.create(
            start_time=LOCAL_TIMEZONE.localize(datetime(2140, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2140, 1, 17, 12)),
            retreat=self.retreat,
        )
        three = RetreatDate.objects.create(
            start_time=LOCAL_TIMEZONE.localize(datetime(2150, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2150, 1, 17, 12)),
            retreat=self.retreat,
        )
        regular_tomato = 37 // 3
        last_tomato = regular_tomato + 37 % 3

        self.assertEqual(regular_tomato, one.number_of_tomatoes)
        self.assertEqual(regular_tomato, two.number_of_tomatoes)
        self.assertEqual(last_tomato, three.number_of_tomatoes)
