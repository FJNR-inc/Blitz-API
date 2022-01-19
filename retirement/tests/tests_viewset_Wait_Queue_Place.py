import json
from datetime import datetime, timedelta
from unittest import mock

import pytz
from django.conf import settings
from django.urls import reverse
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from blitz_api.factories import RetreatFactory, UserFactory, AdminFactory
from ..models import WaitQueuePlace, WaitQueue, WaitQueuePlaceReserved, \
    Retreat, RetreatDate, RetreatType

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


@override_settings(
    LOCAL_SETTINGS={
        "EMAIL_SERVICE": True,
        "FRONTEND_INTEGRATION": {
            "RETREAT_UNSUBSCRIBE_URL": "fake_url",
        }
    }
)
class WaitQueuePlaceTests(APITestCase):

    def setUp(self) -> None:
        self.admin = AdminFactory()

        self.user1 = UserFactory(email='user1@test.com')
        self.user2 = UserFactory(email='user2@test.com')
        self.user3 = UserFactory(email='user3@test.com')
        self.user4 = UserFactory(email='user4@test.com')
        self.user5 = UserFactory(email='user5@test.com')
        self.user6 = UserFactory(email='user6@test.com')
        self.user_cancel = UserFactory()

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

        self.wait_queue_place = WaitQueuePlace.objects.create(
            retreat=self.retreat,
            cancel_by=self.user_cancel
        )

        self.wait_queue_user1 = WaitQueue.objects.create(
            retreat=self.retreat,
            user=self.user1
        )
        self.wait_queue_user2 = WaitQueue.objects.create(
            retreat=self.retreat,
            user=self.user2
        )
        self.wait_queue_user3 = WaitQueue.objects.create(
            retreat=self.retreat,
            user=self.user3
        )
        self.wait_queue_user4 = WaitQueue.objects.create(
            retreat=self.retreat,
            user=self.user4
        )
        self.wait_queue_user5 = WaitQueue.objects.create(
            retreat=self.retreat,
            user=self.user5
        )
        self.wait_queue_user6 = WaitQueue.objects.create(
            retreat=self.retreat,
            user=self.user6
        )

    def check_user_has_reserved_place_notify(
            self,
            user,
            wait_queue_place):
        self.assertTrue(
            WaitQueuePlaceReserved.objects.filter(
                user=user,
                notified=True,
                used=False,
                wait_queue_place=wait_queue_place
            ).exists()
        )

    def check_user_has_reserved_place(
            self,
            user,
            wait_queue_place):
        self.assertTrue(
            WaitQueuePlaceReserved.objects.filter(
                user=user,
                notified=False,
                used=False,
                wait_queue_place=wait_queue_place
            ).exists()
        )

    def check_count_wait_queue_place(self, wait_queue_place, count):
        self.assertEquals(
            WaitQueuePlaceReserved.objects.filter(
                wait_queue_place=wait_queue_place,
                used=False,
            ).count(),
            count
        )

    def check_place_reserved_used(self, wait_queue_place, user):
        self.assertTrue(
            WaitQueuePlaceReserved.objects.get(
                user=user,
                wait_queue_place=wait_queue_place
            ).used
        )

    def test_notify_wait_queue_place(self):
        self.wait_queue_place.notify()

        self.check_user_has_reserved_place_notify(self.user1,
                                                  self.wait_queue_place)
        self.check_count_wait_queue_place(self.wait_queue_place, 1)

        self.wait_queue_place.notify()

        self.check_user_has_reserved_place_notify(self.user2,
                                                  self.wait_queue_place)
        self.check_user_has_reserved_place_notify(self.user1,
                                                  self.wait_queue_place)
        self.check_count_wait_queue_place(self.wait_queue_place, 2)

        wait_queue_place2 = WaitQueuePlace.objects.create(
            retreat=self.retreat,
            cancel_by=self.user_cancel
        )

        wait_queue_place2.notify()

        self.check_user_has_reserved_place_notify(self.user3,
                                                  wait_queue_place2)
        self.check_user_has_reserved_place(self.user2, wait_queue_place2)
        self.check_user_has_reserved_place(self.user1, wait_queue_place2)
        self.check_count_wait_queue_place(wait_queue_place2, 3)

        self.retreat.check_and_use_reserved_place(self.user2)

        self.check_place_reserved_used(wait_queue_place2, self.user2)
        self.check_place_reserved_used(self.wait_queue_place, self.user2)

        self.wait_queue_user2.refresh_from_db()
        self.assertTrue(
            self.wait_queue_user2.used
        )

        self.wait_queue_place.refresh_from_db()
        self.assertFalse(
            self.wait_queue_place.available
        )

        detail, stop = self.wait_queue_place.notify()
        self.assertTrue(stop)
        self.assertEqual(detail, 'Wait queue place not available')

        wait_queue_place2.notify()
        self.check_user_has_reserved_place_notify(self.user4,
                                                  wait_queue_place2)
        self.check_user_has_reserved_place_notify(self.user3,
                                                  wait_queue_place2)
        self.check_user_has_reserved_place(self.user1, wait_queue_place2)
        self.check_count_wait_queue_place(wait_queue_place2, 3)

        FIXED_TIME = self.retreat.start_time - timedelta(days=2)

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            users_notified, stop = wait_queue_place2.notify()
            self.assertIn(self.user5.email, users_notified)
            self.assertIn(self.user6.email, users_notified)
            self.assertFalse(stop)

            self.check_user_has_reserved_place_notify(self.user6,
                                                      wait_queue_place2)
            self.check_user_has_reserved_place_notify(self.user5,
                                                      wait_queue_place2)
            self.check_user_has_reserved_place_notify(self.user4,
                                                      wait_queue_place2)
            self.check_user_has_reserved_place_notify(self.user3,
                                                      wait_queue_place2)
            self.check_user_has_reserved_place(self.user1, wait_queue_place2)
            self.check_count_wait_queue_place(wait_queue_place2, 5)

        FIXED_TIME = self.retreat.start_time + timedelta(days=2)

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            detail, stop = wait_queue_place2.notify()
            self.assertEqual(detail, 'Retreat already started')
            self.assertTrue(stop)

    def test_view_notify_wait_queue_place(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse(
                'retreat:waitqueueplace-notify',
                kwargs={'pk': self.wait_queue_place.id},
            ),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_202_ACCEPTED,
            response.content
        )

        response_data = json.loads(response.content)

        content = {
            'detail': [self.user1.email],
            'wait_queue_place': self.wait_queue_place.id,
            'stop': False
        }

        self.assertEqual(response_data, content)

        self.assertTrue(
            WaitQueuePlaceReserved.objects.filter(
                user=self.user1,
                notified=True,
                wait_queue_place=self.wait_queue_place
            ).exists()
        )

        response = self.client.get(
            reverse(
                'retreat:waitqueueplace-notify',
                kwargs={'pk': self.wait_queue_place.id},
            ),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
            response.content
        )

        response_data = json.loads(response.content)

        content = {
            'detail': "Last notification was sent less than 24h ago.",
            'wait_queue_place': self.wait_queue_place.id,
        }

        self.assertEqual(response_data, content)
