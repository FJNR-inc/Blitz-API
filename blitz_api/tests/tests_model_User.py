from django.utils import timezone
from rest_framework.test import APITestCase

from blitz_api.factories import UserFactory
from tomato.factories import TomatoFactory
from tomato.models import Tomato


class UserTests(APITestCase):
    def test_property_current_month_tomatoes(self):
        """
        Ensure we get the correct value for property current_month_tomatoes
        """
        today = timezone.now()
        user1 = UserFactory()
        user2 = UserFactory()
        user3 = UserFactory()
        t1_1 = TomatoFactory(
            user=user1,
            number_of_tomato=15,
            acquisition_date=today,
            source=Tomato.TOMATO_SOURCE_RETREAT)
        t1_2 = TomatoFactory(
            user=user1,
            acquisition_date=today,
            source=Tomato.TOMATO_SOURCE_CHRONO)
        t1_3 = TomatoFactory(
            user=user1,
            number_of_tomato=12.5,
            acquisition_date=today,
            source=Tomato.TOMATO_SOURCE_MANUAL)
        t1_4 = TomatoFactory(
            user=user1,
            acquisition_date=today,
            source=Tomato.TOMATO_SOURCE_TIMESLOT)
        TomatoFactory(
            user=user1,
            acquisition_date=today - timezone.timedelta(days=31),
            source=Tomato.TOMATO_SOURCE_TIMESLOT)
        TomatoFactory(
            user=user1,
            acquisition_date=today + timezone.timedelta(days=31),
            source=Tomato.TOMATO_SOURCE_CHRONO)

        TomatoFactory(
            user=user2,
            acquisition_date=today - timezone.timedelta(days=31),
            source=Tomato.TOMATO_SOURCE_TIMESLOT)
        TomatoFactory(
            user=user2,
            acquisition_date=today + timezone.timedelta(days=31),
            source=Tomato.TOMATO_SOURCE_CHRONO)
        TomatoFactory(
            user=user2,
            acquisition_date=today,
            source=Tomato.TOMATO_SOURCE_MANUAL)
        TomatoFactory(
            user=user2,
            acquisition_date=today,
            source=Tomato.TOMATO_SOURCE_TIMESLOT)
        self.assertEqual(
            # convert float to avoid Decimal(x), handled by serializer
            float(user1.current_month_tomatoes),
            sum([
                t1_1.number_of_tomato,
                t1_2.number_of_tomato,
                t1_3.number_of_tomato,
                t1_4.number_of_tomato])
        )

        self.assertEqual(user3.current_month_tomatoes, 0)
