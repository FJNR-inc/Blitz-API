from datetime import timedelta

from rest_framework.test import APITestCase

from django.test import override_settings
from django.utils import timezone

from ..models import Workplace, Period


class PictureTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(PictureTests, cls).setUpClass()
        cls.workplace = Workplace.objects.create(
            name="random_workplace",
            details="This is a description of the workplace.",
            seats=40,
            address_line1="123 random street",
            postal_code="123 456",
            state_province="Random state",
            country="Random country",
        )

    def test_create(self):
        """
        Ensure that we can create a period.
        """
        period = Period.objects.create(
            name="random_period",
            workplace=self.workplace,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(weeks=4),
            price=3,
            is_active=True,
        )

        self.assertEqual(period.__str__(), "random_period")
