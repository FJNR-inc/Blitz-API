from datetime import datetime

import pytz
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from rest_framework.test import APITestCase

from blitz_api.factories import UserFactory

from store.models import (
    Order,
    OrderLine,
    Coupon,
)

from retirement.models import (
    Reservation,
    Retreat,
    RetreatDate,
    RetreatType,
)

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)

TAX_RATE = settings.LOCAL_SETTINGS['SELLING_TAX']


class ReservationTests(APITestCase):

    def setUp(self):
        self.user = UserFactory()
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
        )
        RetreatDate.objects.create(
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 17, 12)),
            retreat=self.retreat,
        )
        self.retreat.activate()
        self.order = Order.objects.create(
            user=self.user,
            transaction_date=timezone.now(),
            authorization_id=1,
            settlement_id=1,
        )
        self.order_line = OrderLine.objects.create(
            order=self.order,
            quantity=999,
            content_type=self.retreat_type,
            object_id=1,
        )

    def test_create(self):
        """
        Ensure that we can create a time_slot.
        """
        reservation = Reservation.objects.create(
            user=self.user,
            retreat=self.retreat,
            order_line=self.order_line,
            is_active=True,
        )

        self.assertEqual(str(reservation), str(self.user))

    def test_refund_value_with_coupon(self):
        retreat = Retreat.objects.create(
            name="mega_retreat",
            details="This is a description of the mega retreat.",
            seats=400,
            address_line1="123 random street",
            postal_code="123 456",
            state_province="Random state",
            country="Random country",
            price=100,
            min_day_refund=7,
            min_day_exchange=7,
            refund_rate=90,
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
        )
        RetreatDate.objects.create(
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 17, 12)),
            retreat=retreat,
        )
        retreat.activate()

        order = Order.objects.create(
            user=self.user,
            transaction_date=timezone.now(),
            authorization_id=1,
            settlement_id=1,
        )

        coupon = Coupon.objects.create(
            value=20,
            code="ASD1234E",
            start_time="2019-01-06T15:11:05-05:00",
            end_time="2020-01-06T15:11:06-05:00",
            max_use=100,
            max_use_per_user=2,
            details="detail",
            owner=self.user,
        )

        order_line = OrderLine.objects.create(
            order=order,
            quantity=999,
            content_type=self.retreat_type,
            object_id=1,
            cost=80,
            total_cost=80,
            coupon_real_value=20,
            coupon=coupon
        )

        reservation = Reservation.objects.create(
            user=self.user,
            retreat=retreat,
            order_line=order_line,
            is_active=True,
        )

        refund_value = reservation.get_refund_value()

        self.assertEqual(refund_value, round(72 * (TAX_RATE + 1.0), 2))

    def test_refund_value_100(self):
        retreat = Retreat.objects.create(
            name="mega_retreat",
            details="This is a description of the mega retreat.",
            seats=400,
            address_line1="123 random street",
            postal_code="123 456",
            state_province="Random state",
            country="Random country",
            price=100,
            min_day_refund=7,
            min_day_exchange=7,
            refund_rate=100,
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
        )
        RetreatDate.objects.create(
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 17, 12)),
            retreat=retreat,
        )
        retreat.activate()

        order = Order.objects.create(
            user=self.user,
            transaction_date=timezone.now(),
            authorization_id=1,
            settlement_id=1,
        )

        coupon = Coupon.objects.create(
            value=20,
            code="ASD1234E",
            start_time="2019-01-06T15:11:05-05:00",
            end_time="2020-01-06T15:11:06-05:00",
            max_use=100,
            max_use_per_user=2,
            details="detail",
            owner=self.user,
        )

        order_line = OrderLine.objects.create(
            order=order,
            quantity=999,
            content_type=self.retreat_type,
            object_id=1,
            cost=80,
            total_cost=80,
            coupon_real_value=20,
            coupon=coupon
        )

        reservation = Reservation.objects.create(
            user=self.user,
            retreat=retreat,
            order_line=order_line,
            is_active=True,
        )

        refund_value = reservation.get_refund_value()

        self.assertEqual(refund_value, round(80 * (TAX_RATE + 1.0), 2))

    def test_refund_value_made_by_admin(self):
        """
        Test that a reservation linked to an order made by an admin
        has a refund of 0
        """
        retreat = Retreat.objects.create(
            name="mega_retreat",
            details="This is a description of the mega retreat.",
            seats=400,
            address_line1="123 random street",
            postal_code="123 456",
            state_province="Random state",
            country="Random country",
            price=100,
            min_day_refund=7,
            min_day_exchange=7,
            refund_rate=100,
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
        )
        RetreatDate.objects.create(
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 17, 12)),
            retreat=retreat,
        )
        retreat.activate()

        order = Order.objects.create(
            user=self.user,
            transaction_date=timezone.now(),
            authorization_id=1,
            settlement_id=1,
            is_made_by_admin=True,
        )

        order_line = OrderLine.objects.create(
            order=order,
            quantity=999,
            content_type=self.retreat_type,
            object_id=1,
            cost=80,
            coupon_real_value=20,
        )

        reservation = Reservation.objects.create(
            user=self.user,
            retreat=retreat,
            order_line=order_line,
            is_active=True,
        )

        refund_value = reservation.get_refund_value()

        self.assertEqual(refund_value, 0)
