from datetime import timedelta

from rest_framework.test import APITestCase

from django.utils import timezone

from ..models import Workplace, Period, TimeSlot


class TimeSlotTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(TimeSlotTests, cls).setUpClass()
        cls.workplace = Workplace.objects.create(
            name="random_workplace",
            details="This is a description of the workplace.",
            seats=40,
            address_line1="123 random street",
            postal_code="123 456",
            state_province="Random state",
            country="Random country",
        )
        cls.period = Period.objects.create(
            name="random_period",
            workplace=cls.workplace,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(weeks=4),
            price=3,
            is_active=True,
        )

    def test_create(self):
        """
        Ensure that we can create a time_slot.
        """
        time_slot = TimeSlot.objects.create(
            name="random_time_slot",
            period=self.period,
            price=3,
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=4),
        )

        self.assertEqual(
            time_slot.__str__(),
            str(time_slot.start_time) + " - " + str(time_slot.end_time)
        )

    def test_billing_price(self):
        """
        Ensure we get the price attribute if it is not None when calling
        get_price_or_default()
        """

        time_slot = TimeSlot.objects.create(
            name="random_time_slot",
            period=self.period,
            price=1,
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=4),
        )

        # For this test to make sense, the period price and the timeslot
        # price must not be equal
        self.assertNotEqual(self.period.price, time_slot.price)

        self.assertEqual(time_slot.billing_price, time_slot.price)

    def test_billing_price__price_none(self):
        """
        Ensure we get the period's price if the price attribute is None when
        calling get_price_or_default()
        """

        time_slot = TimeSlot.objects.create(
            name="random_time_slot",
            period=self.period,
            price=None,
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=4),
        )

        self.assertEqual(time_slot.billing_price, self.period.price)

    def test_property_duration(self):
        time_slot = TimeSlot.objects.create(
            name="random_time_slot",
            period=self.period,
            price=3,
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=4, minutes=47),
        )
        self.assertEqual(
            time_slot.duration,
            3600*4 + 60*47
        )

    def test_property_number_of_tomatoes(self):
        time_slot = TimeSlot.objects.create(
            name="random_time_slot",
            period=self.period,
            price=3,
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=4, minutes=47),
        )
        self.assertEqual(
            time_slot.number_of_tomatoes,
            time_slot.duration // 3600
        )
