from datetime import timedelta

from rest_framework.test import APITestCase

from django.utils import timezone

from location.models import Address, Country, StateProvince

from ..models import Workplace, Period, TimeSlot


class TimeSlotTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(TimeSlotTests, cls).setUpClass()
        cls.random_country = Country.objects.create(
            name="Random Country",
            iso_code="RC",
        )
        cls.random_state_province = StateProvince.objects.create(
            name="Random State",
            iso_code="RS",
            country=cls.random_country,
        )
        cls.address = Address.objects.create(
            address_line1='random address 1',
            postal_code='RAN DOM',
            city='random city',
            state_province=cls.random_state_province,
            country=cls.random_country,
        )
        cls.workplace = Workplace.objects.create(
            name="random_workplace",
            details="This is a description of the workplace.",
            seats=40,
            location=cls.address,
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

        self.assertEqual(time_slot.__str__(), "random_time_slot")
