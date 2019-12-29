import json
from datetime import datetime, timedelta
from unittest import mock

import pytz
from django.conf import settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from blitz_api.factories import RetreatFactory, UserFactory, AdminFactory
from ..models import WaitQueuePlace, WaitQueue, WaitQueuePlaceReserved

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


class RetreatTests(APITestCase):

    def setUp(self) -> None:
        self.admin = AdminFactory()

        self.user1 = UserFactory()
        self.user2 = UserFactory()
        self.user3 = UserFactory()
        self.user4 = UserFactory()
        self.user5 = UserFactory()
        self.user6 = UserFactory()
        self.user_cancel = UserFactory()

        self.retreat = RetreatFactory()
        self.retreat.min_day_refund = 7
        self.retreat.save()

        self.wait_queue_place = WaitQueuePlace.objects.create(
            retreat=self.retreat,
            cancel_by=self.user_cancel
        )

        self.wait_queue1 = WaitQueue.objects.create(
            retreat=self.retreat,
            user=self.user1
        )
        self.wait_queue2 = WaitQueue.objects.create(
            retreat=self.retreat,
            user=self.user2
        )
        self.wait_queue3 = WaitQueue.objects.create(
            retreat=self.retreat,
            user=self.user3
        )
        self.wait_queue4 = WaitQueue.objects.create(
            retreat=self.retreat,
            user=self.user4
        )
        self.wait_queue5 = WaitQueue.objects.create(
            retreat=self.retreat,
            user=self.user5
        )
        self.wait_queue6 = WaitQueue.objects.create(
            retreat=self.retreat,
            user=self.user6
        )

    def test_notify_wait_queue_place(self):
        self.wait_queue_place.notify()

        self.assertTrue(
            WaitQueuePlaceReserved.objects.filter(
                user=self.user1,
                notified=True,
                wait_queue_place=self.wait_queue_place
            ).exists()
        )

        self.wait_queue_place.notify()

        self.assertTrue(
            WaitQueuePlaceReserved.objects.filter(
                user=self.user2,
                notified=True,
                wait_queue_place=self.wait_queue_place
            ).exists()
        )

        self.assertTrue(
            WaitQueuePlaceReserved.objects.filter(
                user=self.user1,
                notified=True,
                wait_queue_place=self.wait_queue_place
            ).exists()
        )

        wait_queue_place2 = WaitQueuePlace.objects.create(
            retreat=self.retreat,
            cancel_by=self.user_cancel
        )

        wait_queue_place2.notify()

        self.assertTrue(
            WaitQueuePlaceReserved.objects.filter(
                user=self.user3,
                notified=True,
                wait_queue_place=wait_queue_place2
            ).exists()
        )

        self.assertTrue(
            WaitQueuePlaceReserved.objects.filter(
                user=self.user2,
                notified=False,
                wait_queue_place=wait_queue_place2
            ).exists()
        )

        self.assertTrue(
            WaitQueuePlaceReserved.objects.filter(
                user=self.user1,
                notified=False,
                wait_queue_place=wait_queue_place2
            ).exists()
        )

        self.retreat.check_and_use_reserved_place(self.user2)

        self.assertFalse(
            WaitQueuePlaceReserved.objects.filter(
                user=self.user2,
                wait_queue_place=wait_queue_place2
            ).exists()
        )
        wait_queue_place2.notify()

        self.assertTrue(
            WaitQueuePlaceReserved.objects.filter(
                user=self.user3,
                notified=True,
                wait_queue_place=wait_queue_place2
            ).exists()
        )

        self.assertTrue(
            WaitQueuePlaceReserved.objects.filter(
                user=self.user1,
                notified=True,
                wait_queue_place=wait_queue_place2
            ).exists()
        )

        self.assertFalse(
            WaitQueuePlaceReserved.objects.filter(
                user=self.user4,
                wait_queue_place=wait_queue_place2
            ).exists()
        )

        wait_queue_place2.notify()

        self.assertTrue(
            WaitQueuePlaceReserved.objects.filter(
                user=self.user3,
                notified=True,
                wait_queue_place=wait_queue_place2
            ).exists()
        )

        self.assertTrue(
            WaitQueuePlaceReserved.objects.filter(
                user=self.user1,
                notified=True,
                wait_queue_place=wait_queue_place2
            ).exists()
        )

        self.assertTrue(
            WaitQueuePlaceReserved.objects.filter(
                user=self.user4,
                notified=True,
                wait_queue_place=wait_queue_place2
            ).exists()
        )

        FIXED_TIME = self.retreat.start_time - timedelta(days=2)

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            users_notified, stop = wait_queue_place2.notify()
            self.assertIn(self.user5.email, users_notified)
            self.assertIn(self.user6.email, users_notified)
            self.assertFalse(stop)

        FIXED_TIME = self.retreat.start_time + timedelta(days=2)

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            users_notified, stop = wait_queue_place2.notify()
            self.assertEqual(len(users_notified), 0)
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
            status.HTTP_200_OK,
            response.content
        )

        response_data = json.loads(response.content)

        content = {
            'detail': [self.user1.email],
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
            status.HTTP_200_OK,
            response.content
        )

        response_data = json.loads(response.content)

        content = {
            'detail': "Last notification was sent less than 24h ago.",
        }

        self.assertEqual(response_data, content)
