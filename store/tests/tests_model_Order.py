from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from rest_framework.test import APITestCase

from blitz_api.factories import UserFactory

from workplace.models import TimeSlot, Period

from ..models import Order, OrderLine, Package

TAX = settings.LOCAL_SETTINGS['SELLING_TAX']


class OrderTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(OrderTests, cls).setUpClass()
        cls.user = UserFactory()
        cls.period = Period.objects.create(
            name="random_period",
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(weeks=4),
            price=3,
            is_active=True,
        )
        cls.package_type = ContentType.objects.get_for_model(Package)
        cls.timeslot_type = ContentType.objects.get_for_model(TimeSlot)
        cls.package = Package.objects.create(
            name="extreme_package",
            details="100 reservations package",
            available=True,
            price=400,
            reservations=100,
        )
        cls.order = Order.objects.create(
            user=cls.user,
            transaction_date=timezone.now(),
            authorization_id=1,
            settlement_id=1,
        )
        cls.ts = TimeSlot.objects.create(
            name="random_time_slot",
            period=cls.period,
            price=3,
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=4),
        )
        OrderLine.objects.create(
            order=cls.order,
            quantity=1,
            content_type=cls.package_type,
            object_id=cls.package.id,
            cost=cls.package.price,
            total_cost=cls.package.price,
        )
        OrderLine.objects.create(
            order=cls.order,
            quantity=1,
            content_type=cls.package_type,
            object_id=cls.package.id,
            cost=cls.package.price,
            total_cost=cls.package.price,
        )
        OrderLine.objects.create(
            order=cls.order,
            quantity=2,
            content_type=cls.timeslot_type,
            object_id=1,
        )

    def test_create(self):
        """
        Ensure that we can create a order.
        """
        order = Order.objects.create(
            user=self.user,
            transaction_date=timezone.now(),
            authorization_id=1,
            settlement_id=1,
        )

        self.assertEqual(str(order), '1')

    def test_total_cost(self):
        """
        Ensure that the property methods returns a valid value.
        """
        expected_total_cost = 2 * self.package.price
        self.assertEqual(self.order.total_cost, expected_total_cost)

        tax = (expected_total_cost * Decimal(repr(TAX))).\
            quantize(Decimal('0.01'))
        expected_total_cost_tax = tax + expected_total_cost
        self.assertEqual(
            self.order.total_cost_with_taxes, expected_total_cost_tax * 100)
