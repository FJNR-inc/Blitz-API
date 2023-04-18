import pytz

from django.conf import settings
from django.utils import timezone
from datetime import datetime
from rest_framework.test import APITestCase

from blitz_api.factories import UserFactory
from tomato.factories import TomatoFactory
from tomato.models import Tomato
from blitz_api.factories import (
    RetreatFactory,
    RetreatTypeFactory,
    RetreatDateFactory,
    ReservationFactory,
    TimeSlotFactory,
    TimeSlotReservationFactory,
)

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


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

    def test_get_nb_tomatoes_retreat(self):
        """
        Ensure we get the correct value for property get_nb_tomatoes_retreat
        """
        today = timezone.now()
        user1 = UserFactory()
        user2 = UserFactory()
        type = RetreatTypeFactory()
        r = RetreatFactory(
            number_of_tomatoes=10,
            type=type,
            display_start_time=LOCAL_TIMEZONE.localize(
                datetime(1990, 1, 15, 8))
        )
        date = RetreatDateFactory(retreat=r)
        resa = ReservationFactory(
            retreat=r,
            user=user1,
            is_active=True
        )
        r2 = RetreatFactory(
            number_of_tomatoes=30,
            type=type,
            display_start_time=LOCAL_TIMEZONE.localize(
                datetime(1990, 1, 15, 8))
        )
        date2 = RetreatDateFactory(retreat=r2)
        resa2 = ReservationFactory(
            retreat=r2,
            user=user1,
            is_active=True
        )
        r3 = RetreatFactory(
            number_of_tomatoes=15,
            type=type,
            display_start_time=LOCAL_TIMEZONE.localize(
                datetime(1990, 1, 15, 8))
        )
        date3 = RetreatDateFactory(
            retreat=r3,
            start_time=LOCAL_TIMEZONE.localize(datetime(1990, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(1990, 1, 17, 12))
        )
        resa3 = ReservationFactory(
            retreat=r3,
            user=user1,
            is_active=True
        )
        t1_1 = TomatoFactory(
            user=user1,
            number_of_tomato=r3.number_of_tomatoes,
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
        self.assertEqual(
            user1.get_nb_tomatoes_retreat(),
            {
                'past': t1_1.number_of_tomato,
                'future': r.number_of_tomatoes + r2.number_of_tomatoes,
            })
        self.assertEqual(
            user2.get_nb_tomatoes_retreat(),
            {
                'past': 0,
                'future': 0,
            })

    def test_get_nb_tomatoes_timeslot(self):
        """
        Ensure we get the correct value for property get_nb_tomatoes_timeslot
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
        t1_5 = TomatoFactory(
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

        t1 = TimeSlotFactory()
        r1 = TimeSlotReservationFactory(timeslot=t1, user=user1)

        t2 = TimeSlotFactory()
        r2 = TimeSlotReservationFactory(
            timeslot=t2, is_active=False, user=user1)

        t3 = TimeSlotFactory(
            start_time=LOCAL_TIMEZONE.localize(datetime(1990, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(1990, 1, 16, 8)))
        r3 = TimeSlotReservationFactory(timeslot=t3, user=user1)

        self.assertEqual(
            user1.get_nb_tomatoes_timeslot(),
            {
                'past': t1_4.number_of_tomato + t1_5.number_of_tomato,
                'future': t1.number_of_tomatoes,
            })
        self.assertEqual(
            user3.get_nb_tomatoes_timeslot(),
            {
                'past': 0,
                'future': 0,
            })

    def test_get_number_of_past_tomatoes(self):
        """
        Ensure we get the correct value for property
        get_number_of_past_tomatoes
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
            user1.get_number_of_past_tomatoes(),
            sum([
                t1_1.number_of_tomato,
                t1_2.number_of_tomato,
                t1_3.number_of_tomato,
                t1_4.number_of_tomato])
        )

        self.assertEqual(user3.get_number_of_past_tomatoes(), 0)
